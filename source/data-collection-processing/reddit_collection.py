"""Bounded private-use Reddit capture with refreshable content and Athena verification.

No immutable content copies. Revalidate cached records after 12 hours; discard
unverified content after 24 hours. Search exhaustion never certifies an archive.
"""
import base64
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener
import boto3
from botocore.exceptions import ClientError
from fda_access import NoRedirect

ROOT = Path(__file__).resolve().parent
FIELDS = [('record_id','string'),('record_kind','string'),('parent_id','string'),
          ('subreddit','string'),('title','string'),('body','string'),('source_url','string'),
          ('created_utc','double'),('score','bigint'),('num_comments','bigint'),
          ('observed_utc','double'),('verified_utc','double'),('sector','string'),
          ('capture_mode','string'),('coverage_note','string')]
NOTE = 'Bounded provider search and comment sample; unresolved issuer links; not an exhaustive archive or historical engagement vintage.'


class APIError(Exception):
    pass


class Reddit:
    def __init__(self, config):
        self.config = config; self.calls = 0; self.remaining = None
        self.opener = build_opener(NoRedirect())
        secret = json.loads(boto3.client('secretsmanager',region_name=config['region']).get_secret_value(
            SecretId=config['secret_id'])['SecretString'])
        auth = base64.b64encode((secret[config['client_id_field']] + ':' + secret[config['client_secret_field']]).encode()).decode()
        result = self._request(Request(config['token_endpoint'],
            data=urlencode({'grant_type':'client_credentials'}).encode(),
            headers={'Authorization':'Basic '+auth,'User-Agent':config['user_agent']}))
        self.token = result.get('access_token')
        if not self.token: raise APIError('oauth_no_token')

    def _request(self, request):
        if self.calls >= self.config['max_requests_per_run'] or (self.remaining is not None and self.remaining < 2):
            raise APIError('request_budget')
        if self.calls: time.sleep(1.1)
        self.calls += 1
        try:
            with self.opener.open(request,timeout=30) as response:
                remaining=response.headers.get('x-ratelimit-remaining')
                if remaining is not None:self.remaining=float(remaining)
                raw=response.read(4*1024*1024+1)
            if len(raw)>4*1024*1024:raise APIError('response_size_limit')
            return json.loads(raw)
        except HTTPError as exc:
            code=exc.code;exc.close();raise APIError('reddit_http_'+str(code)) from None
        except APIError:raise
        except Exception:raise APIError('reddit_transport_error') from None

    def get(self,path,params):
        return self._request(Request('https://oauth.reddit.com'+path+'?'+urlencode(params),
            headers={'Authorization':'Bearer '+self.token,'User-Agent':self.config['user_agent']}))


def normalize(child, sector, mode, now):
    kind=child.get('kind');p=child.get('data',{})
    if kind not in ('t1','t3') or not isinstance(p,dict):return None
    name=p.get('name') or (kind+'_'+p.get('id',''))
    if not p.get('id') or p.get('author') in (None,'[deleted]') or p.get('removed_by_category'):
        return None
    text=p.get('body' if kind=='t1' else 'selftext','') or ''
    if text in ('[deleted]','[removed]'):return None
    created=p.get('created_utc')
    if not isinstance(created,(int,float)) or created>now+300:return None
    if created<1609459200:return None
    url=p.get('permalink','')
    return dict(record_id=name,record_kind='comment' if kind=='t1' else 'post',parent_id=p.get('parent_id',''),
        subreddit=p.get('subreddit',''),title=p.get('title',''),body=text,
        source_url='https://www.reddit.com'+url if url.startswith('/') else '',
        created_utc=created,score=int(p.get('score') or 0),num_comments=int(p.get('num_comments') or 0),
        observed_utc=now,verified_utc=now,sector=sector,capture_mode=mode,coverage_note=NOTE)


def children(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('data',{}).get('children'),list):
        raise APIError('invalid_listing')
    return payload['data']['children']


def comment_children(listing):
    for child in children(listing):
        if child.get('kind')=='t1':
            yield child
            replies=child.get('data',{}).get('replies')
            if isinstance(replies,dict):yield from comment_children(replies)


def revalidate(api, records, now):
    stale=[k for k,r in records.items() if now-r['verified_utc']>=12*3600]
    for start in range(0,len(stale),100):
        ids=stale[start:start+100]
        result=api.get('/api/info',{'id':','.join(ids),'raw_json':1})
        replacement={}
        for child in children(result):
            name=child.get('data',{}).get('name')
            if name not in ids:continue
            prior=records[name]
            row=normalize(child,prior['sector'],prior['capture_mode'],now)
            if row:
                row['observed_utc']=prior['observed_utc'];replacement[name]=row
        for name in ids:records.pop(name,None)
        records.update(replacement)


def trim(records,now,max_records,max_bytes):
    kept={};encoded=[];size=0
    for row in sorted(records.values(),key=lambda r:r['verified_utc'],reverse=True):
        if now-row['verified_utc']>=24*3600:continue
        line=(json.dumps(row,separators=(',',':'))+'\n').encode()
        if len(kept)>=max_records or size+len(line)>max_bytes:continue
        kept[row['record_id']]=row;encoded.append(line);size+=len(line)
    return kept,b''.join(encoded)


def capture(api,records,state,config,report):
    now=time.time()
    revalidate(api,records,now)
    for sector,query in config['queries'].items():
        for mode in ('daily','historical_sample'):
            scope=sector+':'+mode
            prior=state.get(scope,{})
            if mode=='historical_sample' and prior.get('exhausted') and now-prior.get('checked_utc',0)<7*86400:continue
            params={'q':query,'sort':'new' if mode=='daily' else 'top','t':'week' if mode=='daily' else 'all',
                    'limit':100,'type':'link','raw_json':1}
            if mode=='historical_sample' and prior.get('after'):params['after']=prior['after']
            result=api.get('/search',params);posts=children(result)
            after=result['data'].get('after')
            if after and after==params.get('after'):raise APIError('search_cursor_stalled')
            count=0
            for child in posts:
                row=normalize(child,sector,mode,now)
                if row:records[row['record_id']]=row;count+=1
            report['scopes'].append({'sector':sector,'mode':mode,'returned':len(posts),'retained':count,'has_more':bool(after)})
            if mode=='historical_sample':state[scope]={'after':after,'exhausted':not after,'checked_utc':now}
            if mode=='daily':
                threads=[c['data']['id'] for c in posts if c.get('kind')=='t3' and c['data'].get('num_comments',0)>0][:2]
                for thread in threads:
                    payload=api.get('/comments/'+thread,{'limit':50,'depth':3,'raw_json':1,'sort':'new'})
                    if not isinstance(payload,list) or len(payload)!=2:raise APIError('comments_shape')
                    for child in comment_children(payload[1]):
                        row=normalize(child,sector,mode,now)
                        if row:records[row['record_id']]=row


def publish_table(glue,bucket,prefix):
    location='s3://'+bucket+'/'+prefix+'/records/'
    table={'Name':'reddit_records','TableType':'EXTERNAL_TABLE',
        'Parameters':{'classification':'json','optima_owner':'reddit-refreshable-1'},
        'StorageDescriptor':{'Columns':[{'Name':n,'Type':t} for n,t in FIELDS], 'Location':location,
         'InputFormat':'org.apache.hadoop.mapred.TextInputFormat',
         'OutputFormat':'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
         'SerdeInfo':{'SerializationLibrary':'org.openx.data.jsonserde.JsonSerDe'}}}
    try:
        existing=glue.get_table(DatabaseName='optima_social_research',Name='reddit_records')['Table']
        if existing.get('Parameters',{}).get('optima_owner')!='reddit-refreshable-1' or existing['StorageDescriptor']['Location']!=location:
            raise APIError('table_ownership_mismatch')
    except glue.exceptions.EntityNotFoundException:
        glue.create_table(DatabaseName='optima_social_research',TableInput=table)


def verify(athena,expected):
    query=athena.start_query_execution(QueryString='SELECT count(*) AS records FROM optima_social_research.reddit_records',
        WorkGroup='optima-social-research',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId']
    for _ in range(45):
        result=athena.get_query_execution(QueryExecutionId=query)['QueryExecution'];status=result['Status']['State']
        if status=='SUCCEEDED':
            rows=athena.get_query_results(QueryExecutionId=query,MaxResults=2)['ResultSet']['Rows']
            count=int(rows[1]['Data'][0]['VarCharValue'])
            if count!=expected:raise APIError('athena_count_mismatch')
            return {'query_id':query,'records':count,'status':'verified'}
        if status in ('FAILED','CANCELLED'):raise APIError('athena_query_'+status.lower())
        time.sleep(1)
    athena.stop_query_execution(QueryExecutionId=query)
    raise APIError('athena_query_timeout')


def main():
    with (ROOT/'.reddit-collection.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return 0
        config=json.loads((ROOT/'config/reddit-access.json').read_text())
        if not config['collection_enabled']:return 0
        s3=boto3.client('s3',region_name=config['region']);bucket=config['bucket'];prefix=config['prefix']
        report={'at':datetime.now(timezone.utc).isoformat(),'scopes':[],'historical_complete':False}
        def read(key,default):
            try:return s3.get_object(Bucket=bucket,Key=prefix+'/'+key)['Body'].read()
            except ClientError as exc:
                if exc.response['Error']['Code']=='NoSuchKey':return default
                raise
        def put(key,body):
            s3.put_object(Bucket=bucket,Key=prefix+'/'+key,Body=body,ContentType='application/json',ServerSideEncryption='AES256')
        try:
            if s3.get_bucket_versioning(Bucket=bucket).get('Status') in ('Enabled','Suspended'):
                raise APIError('reddit_requires_unversioned_storage')
            raw=read('records/current.jsonl',b'')
            records={r['record_id']:r for r in (json.loads(line) for line in raw.splitlines())}
            state=json.loads(read('state.json',b'{}'))
            # Expire content even if OAuth or upstream access subsequently fails.
            records,body=trim(records,time.time(),config['max_records'],config['max_bytes'])
            put('records/current.jsonl',body)
            try:
                api=Reddit(config);capture(api,records,state,config,report)
                report['requests']=api.calls
            except Exception as exc:
                report['capture_error']=str(exc) if isinstance(exc,APIError) else type(exc).__name__
            records,body=trim(records,time.time(),config['max_records'],config['max_bytes'])
            put('records/current.jsonl',body)
            put('state.json',json.dumps(state).encode())
            report.update(records=len(records),posts=sum(r['record_kind']=='post' for r in records.values()),
                          comments=sum(r['record_kind']=='comment' for r in records.values()))
            publish_table(boto3.client('glue',region_name=config['region']),bucket,prefix)
            report['athena']=verify(boto3.client('athena',region_name=config['region']),len(records))
            report['status']='partial' if report.get('capture_error') else 'captured_and_verified'
        except Exception as exc:
            report['status']='failed';report['error']=str(exc) if isinstance(exc,APIError) else type(exc).__name__
        put('latest-report.json',json.dumps(report).encode())
        (ROOT/'reports/reddit-collection-latest.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report),flush=True)
        return int(report['status']!='captured_and_verified')


if __name__=='__main__':raise SystemExit(main())
