"""Bounded CNINFO/OpenDART index rows paired with archived original documents."""
import hashlib,io,json,re
from datetime import date,timedelta,datetime
from urllib.parse import urlencode,urlsplit,urljoin
import requests
from zoneinfo import ZoneInfo
from regulatory_collection import require,SourceIssue
from research_contract import digest
from collection_storage import write_json

LIMIT=16*1024*1024

def request(client,url,params,*,post=False,key=None):
 allowed={('www.cninfo.com.cn','/new/hisAnnouncement/query'),('opendart.fss.or.kr','/api/list.json'),('opendart.fss.or.kr','/api/document.xml')}
 u=urlsplit(url);require(u.scheme=='https'and(u.hostname,u.path)in allowed,'filing_unapproved_request')
 public=url+('?'+urlencode(params)if params else'');query={**params,**({'crtfc_key':key}if key else{})}
 from constellation.shared_limits import admit
 admit(url)
 try:
  with requests.request('POST'if post else'GET',url,**({'data':query}if post else{'params':query}),headers={'User-Agent':'ConstellationResearch/1.0 (support@optima-holdings.com)','Referer':'https://www.cninfo.com.cn/','X-Requested-With':'XMLHttpRequest'},timeout=(10,40),stream=True,allow_redirects=False)as response:
   chunks=[];size=0
   for chunk in response.iter_content(65536):
    size+=len(chunk);require(size<=LIMIT,'filing_response_too_large');chunks.append(chunk)
   raw=b''.join(chunks)
   if key and not raw.startswith(b'PK'):raw=raw.replace(key.encode(),b'[REDACTED]')
   client.save(raw,public,response.headers.get('Content-Type','application/octet-stream'));require(response.status_code==200,'filing_provider_http_'+str(response.status_code))
   return raw,dict(client.evidence[-1])
 except SourceIssue:raise
 except Exception as exc:raise SourceIssue('filing_transport_'+type(exc).__name__,True)from None

def original(client,source,filing,key=None):
 dart=source=='south_korea_fss_opendart';rid=str(filing['rcept_no'if dart else'announcementId']);require(bool(re.fullmatch(r'\d{10,20}',rid)),'filing_invalid_receipt_identity')
 url='https://opendart.fss.or.kr/api/document.xml?rcept_no='+rid if dart else urljoin('https://static.cninfo.com.cn/',filing['adjunctUrl'])
 if not dart:
  from regional_source_review import in_scope
  require(in_scope(url,source)and urlsplit(url).path.rsplit('/',1)[-1].lower()==rid+'.pdf','cninfo_document_identity_mismatch')
 registry='operations/specialists/filing-documents/'+source+'/'+rid+'.json';stored=client.store.get(registry)
 if stored:
  cached=json.loads(stored.body);require(cached['source_record_id']==rid and cached['source_url']==url,'filing_document_registry_mismatch');ref=cached['artifact'];client.evidence.append(ref);return ref,None
 try:
  if dart:raw,ref=request(client,'https://opendart.fss.or.kr/api/document.xml',{'rcept_no':rid},key=key)
  else:
   # Existing GET transport retains provider bytes, TLS checks, size limits and evidence.
   raw=client.get(url);ref=dict(client.evidence[-1])
  valid=raw.startswith(b'PK\x03\x04')if dart else raw.startswith(b'%PDF-')and b'%%EOF'in raw[-4096:]
  if dart and not valid:
   code=None
   try:code=json.loads(raw).get('status')
   except(ValueError,AttributeError):pass
   if code in ('020','800'):raise SourceIssue('dart_provider_status_'+code,True)
  if not valid:return None,{'reason':'provider_original_not_available','response_evidence':ref}
  value={'source_record_id':rid,'source_url':url,'artifact':ref};write_json(client.store,registry,value);return ref,None
 except SourceIssue as exc:
  if dart and exc.code in ('dart_provider_status_020','dart_provider_status_800','filing_provider_http_429'):
   raise
  return None,{'reason':exc.code}

def fetch(client,job,cursor,item):
 dart=job['source']=='south_korea_fss_opendart';source=job['source'];p=job['parameters'];start=p.get('data_start',job['start']);end=p.get('data_end',job['end']);last=(date.fromisoformat(end)-timedelta(days=1)).isoformat();state=json.loads(cursor)if cursor else{};page=int(state.get('page',1));offset=int(state.get('offset',0));key=None
 if dart:
  from additional_source_apis import credentials
  key=credentials().get('dart');require(bool(key),'additional_key_missing');endpoint='https://opendart.fss.or.kr/api/list.json';params={'bgn_de':start.replace('-',''),'end_de':last.replace('-',''),'page_no':page,'page_count':100,'sort':'date','sort_mth':'asc'}
 else:endpoint='https://www.cninfo.com.cn/new/hisAnnouncement/query';params={'pageNum':page,'pageSize':100,'column':'szse','tabName':'fulltext','seDate':start+'~'+last}
 index_identity=(endpoint,tuple(sorted(params.items())),(state.get('index_evidence')or{}).get('sha256'))
 cached=getattr(client,'_dart_index_cache',None) if dart else None
 if cached and cached[0]==index_identity:
  _, data, ref=cached
 else:
  if state.get('index_evidence'):
   ref=state['index_evidence'];saved=client.store.get(ref['key']);require(saved is not None and hashlib.sha256(saved.body).hexdigest()==ref['sha256'],'filing_cached_index_mismatch');raw=saved.body
  else:raw,ref=request(client,endpoint,params,post=not dart,key=key)
  try:data=json.loads(raw)
  except(ValueError,UnicodeDecodeError):raise SourceIssue('filing_invalid_index_json')from None
  if dart:client._dart_index_cache=((endpoint,tuple(sorted(params.items())),ref['sha256']),data,ref)
 if not any(x.get('sha256')==ref['sha256'] for x in client.evidence):client.evidence.append(ref)
 if dart:
  if data.get('status')=='013':client.expected_records=0;return [],None
  require(data.get('status')=='000','dart_provider_status_'+str(data.get('status')));entries=data['list'];total=int(data['total_count']);pages=int(data['total_page'])
 else:entries=data.get('announcements');total=int(data.get('totalRecordNum',0));pages=int(data.get('totalpages',0))
 require(isinstance(entries,list)and all(isinstance(v,dict)for v in entries),'filing_index_shape')
 if state:require(state['total']==total,'source_changed_refresh_required')
 client.expected_records=total
 if not total:require(not entries,'filing_zero_count_with_rows');return [],None
 require(0<=offset<len(entries),'filing_page_truncated')
 batch=min(8,max(1,getattr(client,'dart_batch_size',1))) if dart else 1
 stop=min(offset+batch,len(entries));rows=[]
 for filing in entries[offset:stop]:
  rid=str(filing['rcept_no'if dart else'announcementId'])
  day=datetime.strptime(filing['rcept_dt'],'%Y%m%d').date().isoformat()if dart else datetime.fromtimestamp(filing['announcementTime']/1000,ZoneInfo('Asia/Shanghai')).date().isoformat()
  require(start<=day<end,'filing_outside_requested_period')
  client.evidence[:]=[ref]
  doc,error=original(client,source,filing,key)
  value={'filing':filing,'primary_document':doc,'document_error':error,'index_request':{'method':'GET'if dart else'POST','endpoint':endpoint,'parameters':params},'index_evidence':ref}
  row=item(rid,value,doc['source_url']if doc else endpoint,day,basis='provider')
  if batch>1:row['filing_evidence']=list(client.evidence)
  rows.append(row)
 if stop<len(entries):following={'page':page,'offset':stop,'total':total,'index_evidence':ref}
 elif page<pages:following={'page':page+1,'offset':0,'total':total}
 else:following=None
 return rows,json.dumps(following)if following else None
