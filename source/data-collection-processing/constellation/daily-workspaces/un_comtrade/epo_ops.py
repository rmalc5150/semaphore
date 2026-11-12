"""EPO OPS applicant discovery and INPADOC events; current snapshots, not vintages."""
from contextlib import contextmanager
from datetime import date,datetime,timedelta,timezone
import hashlib,json,re,time
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
import requests
from regulatory_collection import SourceIssue,require

BASE='https://ops.epo.org/3.2/'
OPS='{http://ops.epo.org}'
EX='{http://www.epo.org/exchange}'
MAX_BYTES=8*1024**2
_CONTROL=None
_TOKEN=None
_EXPIRES=0

def control():
    global _CONTROL
    if _CONTROL is None:
        from constellation.control import Control
        _CONTROL=Control()
    return _CONTROL

@contextmanager
def request_slot():
    """One OPS request at a time across hosts; 3,000/day and 512 MiB/7 days."""
    c=control();day=datetime.now(timezone.utc).date();cutoff=(day-timedelta(days=6)).isoformat()
    with c.db() as q:
        q.execute("SELECT GET_LOCK('constellation:epo:request',10) AS acquired")
        require(q.fetchone()['acquired']==1,'epo_concurrency_deferred')
        try:
            q.execute('INSERT INTO backfill_quotas(source_key,quota_day) VALUES(%s,%s) ON DUPLICATE KEY UPDATE source_key=VALUES(source_key)',('epo_ops',day))
            q.execute('SELECT used_requests,next_request_at FROM backfill_quotas WHERE source_key=%s AND quota_day=%s',('epo_ops',day));r=q.fetchone()
            require(r['used_requests']<3000,'epo_daily_request_budget')
            q.execute('SELECT COALESCE(SUM(used_requests),0) AS used_bytes FROM backfill_quotas WHERE source_key=%s AND quota_day>=%s',('epo_ops_bytes',cutoff))
            require(int(q.fetchone()['used_bytes'])+MAX_BYTES+65536<=512*1024**2,'epo_weekly_byte_budget')
            time.sleep(max(0,float(r['next_request_at'])-time.time()))
            q.execute('UPDATE backfill_quotas SET used_requests=used_requests+1,next_request_at=%s WHERE source_key=%s AND quota_day=%s',(int(time.time())+3,'epo_ops',day))
            # Commit reservation before HTTP, while keeping the session named lock.
            q.connection.commit()
            yield q,day
        finally:
            q.execute("SELECT RELEASE_LOCK('constellation:epo:request')")

def response(method,url,**kw):
    try:
        with request_slot() as (q,day):
            size=0
            try:
                with requests.request(method,url,timeout=(10,45),stream=True,allow_redirects=False,**kw) as r:
                    chunks=[]
                    for chunk in r.iter_content(65536):
                        size+=len(chunk)
                        require(size<=MAX_BYTES,'epo_response_too_large')
                        chunks.append(chunk)
                    return r.status_code,b''.join(chunks),r.headers
            finally:
                if size:
                    q.execute('INSERT INTO backfill_quotas(source_key,quota_day,used_requests) VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE used_requests=used_requests+VALUES(used_requests)',('epo_ops_bytes',day,size))
                    q.connection.commit()

    except SourceIssue:raise
    except Exception:raise SourceIssue('epo_request_failed',True) from None

def token():
    global _TOKEN,_EXPIRES
    if _TOKEN and time.monotonic()<_EXPIRES:return _TOKEN
    from additional_source_apis import credentials
    values=credentials();pair=tuple(values.get(k,'').strip() for k in ('EPO-consumer','EPO-consumer-secret'))
    require(all(pair),'epo_credentials_missing')
    status,body,_=response('POST',BASE+'auth/accesstoken',auth=pair,data={'grant_type':'client_credentials'})
    require(status==200,'epo_oauth_http_'+str(status))
    try:d=json.loads(body);_TOKEN=d['access_token'];_EXPIRES=time.monotonic()+max(0,int(d['expires_in'])-60)
    except (ValueError,KeyError,TypeError):raise SourceIssue('epo_oauth_shape') from None
    return _TOKEN

def xml(client,path,params=None):
    require(path.startswith(('rest-services/published-data/search','rest-services/legal/publication/docdb/')),'epo_unreviewed_endpoint')
    url=BASE+path;access=token();status,body,headers=response('GET',url,params=params,headers={'Authorization':'Bearer '+access,'Accept':'application/xml','User-Agent':'ConstellationResearch/1.0 (support@optima-holdings.com)'})
    if status==401:
        global _EXPIRES
        _EXPIRES=0
        raise SourceIssue('source_http_401',True)
    from additional_source_apis import credentials
    for value in [access,credentials().get('EPO-consumer',''),credentials().get('EPO-consumer-secret','')]:
        if value:body=body.replace(value.encode(),b'[REDACTED]')
    client.save(body,url+('?' +urlencode(params) if params else ''),headers.get('Content-Type','application/xml'))
    try:root=ET.fromstring(body)
    except ET.ParseError:raise SourceIssue('epo_invalid_xml') from None
    if status==404:
        code=next((x.text or '' for x in root.iter() if x.tag.rsplit('}',1)[-1]=='code'),'')
        message=' '.join(root.itertext()).lower()
        if code in {'CLIENT.EntityNotFound','SERVER.EntityNotFound'} and ('no results' in message or 'no data' in message or 'no legal information' in message):return None
    require(status==200,'source_http_'+str(status))
    require(root.tag==OPS+'world-patent-data','epo_response_shape')
    return root

def legal_rows(root,reference,p,item):
    if root is None:return []
    rows=[];seen=set()
    for member in root.findall('.//'+OPS+'family-member'):
        ids=[ET.tostring(n,encoding='unicode') for n in member.findall(EX+'publication-reference')+member.findall(EX+'application-reference')]
        for event in member.findall(OPS+'legal'):
            fields={n.tag.rsplit('}',1)[-1]:(n.text or '').strip() for n in event.iter() if n is not event and not list(n)}
            raw_day=fields.get('L007EP');day=None
            if raw_day:
                try:day=date.fromisoformat(raw_day).isoformat()
                except ValueError:pass
            if day and not ('2016-01-01'<=day<p['snapshot_end']):continue
            original=ET.tostring(event,encoding='unicode')
            # Provider amendments change the payload, while exact repeated events collapse.
            identity=hashlib.sha256(json.dumps([reference,ids,original],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
            if identity in seen:continue
            seen.add(identity)
            data={'publication_reference':reference,'family_id':member.get('family-id'),'member_identifiers_xml':ids,'event_attributes':event.attrib,'fields':fields,'event_xml':original,'date_basis':'gazette_date' if day else 'unknown','effective_date_raw':fields.get('L525EP'),'provider_created_date_raw':fields.get('L019EP'),'provider_exchanged_date_raw':fields.get('L018EP'),'candidate_applicant':p.get('applicant'),'candidate_company_id':p.get('company_id'),'entity_link_status':'unreviewed','snapshot_not_original_vintage':True}
            rows.append(item(identity,data,BASE+'rest-services/legal/publication/docdb/'+reference,day,basis='derived'))
    return rows

def registry(reference):
    c=control();bucket=c.config['bucket'];digest=hashlib.sha256(reference.encode()).hexdigest();key=c.config['prefix']+'/epo/registry/'+digest[0]+'/'+reference+'.json'
    # Same immutable reference; known-patent refresh can safely run before a page commit.
    c.s3.put_object(Bucket=bucket,Key=key,Body=json.dumps({'reference':reference}).encode(),ServerSideEncryption='AES256')

def refresh(client,job,cursor,item):
    p=job['parameters'];state=json.loads(cursor) if cursor else {};c=control();prefix=c.config['prefix']+'/epo/registry/'+p['shard']+'/'
    if not state:
        try:
            response=c.s3.get_object(Bucket=c.config['bucket'],Key=c.config['prefix']+'/epo/refresh/'+p['shard']+'.json');state=json.loads(response['Body'].read());response['Body'].close();state['visited']=0
        except c.s3.exceptions.NoSuchKey:state={}
    query={'Bucket':c.config['bucket'],'Prefix':prefix,'MaxKeys':1}
    if state.get('after'):query['StartAfter']=state['after']
    objects=c.s3.list_objects_v2(**query).get('Contents',[])
    if not objects:
        client.epo_refresh_after='';return [],None
    key=objects[0]['Key'];reference=key.rsplit('/',1)[-1].removesuffix('.json');require(bool(re.fullmatch(r'[A-Z]{2}\.[A-Za-z0-9]+\.[A-Z][0-9A-Z]*',reference)),'epo_invalid_reference')
    rows=legal_rows(xml(client,'rest-services/legal/publication/docdb/'+reference),reference,p,item);client.epo_refresh_after=key
    visited=state.get('visited',0)+1
    return rows,json.dumps({'after':key,'visited':visited}) if visited<50 else None

def after_commit(client,job):
    if not hasattr(client,'epo_refresh_after'):return
    c=control();c.s3.put_object(Bucket=c.config['bucket'],Key=c.config['prefix']+'/epo/refresh/'+job['parameters']['shard']+'.json',Body=json.dumps({'after':client.epo_refresh_after}).encode(),ServerSideEncryption='AES256')

def fetch(client,job,cursor,item):
    p=job['parameters']
    if p.get('purpose')=='refresh':return refresh(client,job,cursor,item)
    state=json.loads(cursor) if cursor else {'ranges':[[p['discovery_start'],p['discovery_end']]],'offset':1,'pending':[],'seen':[],'seen_base':0}
    # Retain compatibility with already committed startup cursors.
    if 'seen' not in state:state.update(seen=[],seen_base=state['offset']-1)
    if not state['pending']:
        if not state['ranges']:return [],None
        begin,end=state['ranges'][0];applicant=p['applicant'];require('"' not in applicant and '\\' not in applicant,'epo_invalid_applicant')
        aliases=p.get('applicant_aliases',[applicant]);require(all(isinstance(a,str) and '"' not in a and '\\' not in a for a in aliases),'epo_invalid_applicant')
        query='('+' or '.join('pa="'+a+'"' for a in aliases)+') and pd within "'+begin.replace('-','')+' '+(date.fromisoformat(end)-timedelta(days=1)).strftime('%Y%m%d')+'"'
        root=xml(client,'rest-services/published-data/search',{'q':query,'Range':str(state['offset'])+'-'+str(state['offset']+24)})
        if root is None:
            require(state['offset']==1 and not state.get('total'),'source_changed_refresh_required')
            state['ranges'].pop(0);state.update(offset=1,seen=[],seen_base=0);state.pop('total',None);return [],json.dumps(state) if state['ranges'] else None
        search=root.find(OPS+'biblio-search');require(search is not None,'epo_search_shape');total=int(search.get('total-result-count','-1'));require(total>=0,'epo_search_total')
        if total>2000:
            a=date.fromisoformat(begin);b=date.fromisoformat(end);require((b-a).days>1,'epo_single_day_exceeds_search_limit');middle=a+timedelta(days=(b-a).days//2);state['ranges'][:1]=[[begin,middle.isoformat()],[middle.isoformat(),end]];state.update(offset=1,seen=[],seen_base=0);state.pop('total',None);return [],json.dumps(state)
        if 'total' in state:require(state['total']==total,'source_changed_refresh_required')
        state['total']=total;refs=[]
        for doc in search.findall('.//'+OPS+'publication-reference/'+EX+'document-id'):
            if doc.get('document-id-type')!='docdb':continue
            ref='.'.join((doc.findtext(EX+'country') or '',doc.findtext(EX+'doc-number') or '',doc.findtext(EX+'kind') or ''))
            require(bool(re.fullmatch(r'[A-Z]{2}\.[A-Za-z0-9]+\.[A-Z][0-9A-Z]*',ref)),'epo_invalid_reference');refs.append(ref)
        require(len(refs)==len(set(refs)),'epo_duplicate_search_references');require(not set(refs).intersection(state['seen']),'source_changed_refresh_required');require(len(refs)==min(25,max(0,total-state['offset']+1)),'epo_truncated_search_page');state['pending']=refs;state['seen']+=refs
        state['offset']+=len(refs)
        if not refs:state['ranges'].pop(0);state.update(offset=1,seen=[],seen_base=0);state.pop('total',None);return [],json.dumps(state) if state['ranges'] else None
    reference=state['pending'][0];rows=legal_rows(xml(client,'rest-services/legal/publication/docdb/'+reference),reference,p,item);registry(reference);state['pending'].pop(0)
    if not state['pending'] and state['offset']>state['total']:
        require(len(state['seen'])+state['seen_base']==state['total'],'epo_search_reference_count_mismatch')
        state['ranges'].pop(0);state.update(offset=1,seen=[],seen_base=0);state.pop('total',None)
    return rows,json.dumps(state,separators=(',',':')) if state['pending'] or state['ranges'] else None
