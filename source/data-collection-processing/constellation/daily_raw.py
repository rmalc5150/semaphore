"""Capture recent closed UTC days on t3 using the raw providers' shared budgets."""
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
import hashlib
import json
import os
import time
import uuid

import requests
from constellation.control import Control,canonical
from constellation.sources import PROVIDERS,VERSION,request,parse,identity
from public_source_capture import BUCKET,PREFIX,read_json,put,encode


@contextmanager
def connection(control,source):
    if source!='arxiv':yield;return
    with control.db() as cursor:
        cursor.execute("SELECT GET_LOCK('constellation:arxiv:http',20) AS acquired")
        acquired=cursor.fetchone()['acquired']==1
        if not acquired:raise RuntimeError('daily_provider_connection_deferred')
        try:yield
        finally:cursor.execute("SELECT RELEASE_LOCK('constellation:arxiv:http')")


def reserve(control,source):
    policy=PROVIDERS[source];day=datetime.now(timezone.utc).date().isoformat()
    for _ in range(20):
        with control.db() as cursor:
            cursor.execute('INSERT INTO backfill_quotas(source_key,quota_day) VALUES(%s,%s) ON DUPLICATE KEY UPDATE source_key=VALUES(source_key)',(source,day))
            cursor.execute('SELECT *,UNIX_TIMESTAMP() AS now_epoch FROM backfill_quotas WHERE source_key=%s AND quota_day=%s FOR UPDATE',(source,day));row=cursor.fetchone()
            if row['used_requests']>=policy['daily_budget']:return False
            if row['next_request_at']<=row['now_epoch']:
                cursor.execute('UPDATE backfill_quotas SET next_request_at=UNIX_TIMESTAMP()+%s,used_requests=used_requests+1 WHERE source_key=%s AND quota_day=%s',(policy['interval_seconds'],source,day));return True
        time.sleep(1)
    return False


def page(control,source,spec,state):
    cursor=state.get('cursor');url,params=request(spec,cursor)
    with connection(control,source):
        if not reserve(control,source):return {**state,'status':'deferred_not_a_gap','reason':'shared_provider_budget_or_spacing'}
        with requests.get(url,params=params,stream=True,timeout=(10,30),allow_redirects=False,headers={'User-Agent':'ConstellationResearch/1.0 (support@optima-holdings.com)'}) as response:
            chunks=[];size=0
            for chunk in response.iter_content(65536):
                size+=len(chunk)
                if size>16*1024**2:raise ValueError('daily_response_too_large')
                chunks.append(chunk)
            body=b''.join(chunks);checksum=hashlib.sha256(body).hexdigest();raw_key=PREFIX+'/objects/'+source+'/'+checksum
            put(control.s3,raw_key,body,response.headers.get('Content-Type','application/octet-stream'))
            check=control.s3.get_object(Bucket=BUCKET,Key=raw_key)
            try:
                if hashlib.sha256(check['Body'].read()).hexdigest()!=checksum:raise ValueError('daily_raw_readback_mismatch')
            finally:check['Body'].close()
            if response.status_code not in (200,204):raise ValueError('daily_source_http_'+str(response.status_code))
            rows,following=parse(spec,body,cursor,response.status_code)
    ids=[identity(spec,row) for row in rows];seen=set(state.get('seen',[]))
    if len(ids)!=len(set(ids)) or seen.intersection(ids):raise ValueError('daily_duplicate_provider_ids')
    at=datetime.now(timezone.utc).isoformat();records=[]
    for provider_id,row in zip(ids,rows):
        records.append({'source':source,'partition_start':spec['start'],'partition_end':spec['end'],'source_record_id':provider_id,'retrieved_at':at,'payload_json':json.dumps(row,ensure_ascii=False),'raw_uri':'s3://'+BUCKET+'/'+raw_key})
    if records:put(control.s3,'research-data/constellation-backfill/daily-raw/records/'+uuid.uuid4().hex+'.jsonl',b''.join(encode(r) for r in records),'application/x-ndjson')
    seen.update(ids)
    return {'status':'complete' if following is None else 'in_progress','cursor':following,'seen':sorted(seen),'record_count':len(seen),'updated_at':at,'raw_uri':'s3://'+BUCKET+'/'+raw_key}


def main():
    if os.environ.get('CONSTELLATION_ROLE','controller')!='controller':raise ValueError('daily_raw_requires_t3')
    control=Control()
    if not control.daily_allowed():return
    today=datetime.now(timezone.utc).date();results=[]
    for source,provider in PROVIDERS.items():
        for offset in range(1,8):
            end=today-timedelta(days=offset-1);start=end-timedelta(days=1)
            key='research-data/constellation-backfill/daily-raw/states/'+today.isoformat()+'/'+source+'/'+start.isoformat()+'.json'
            state,token=read_json(control.s3,key);state=state or {}
            if state.get('status')=='complete':continue
            spec={'source_key':source,'dataset':provider['dataset'],'geography':'global','start':start.isoformat(),'end':end.isoformat(),'edition':'current_retrieval','extractor_version':VERSION,'parameters':{}}
            try:updated=page(control,source,spec,state)
            except Exception as exc:updated={**state,'status':'failed','reason':str(exc) if type(exc) is ValueError else type(exc).__name__,'updated_at':datetime.now(timezone.utc).isoformat()}
            put(control.s3,key,encode(updated),**({'IfMatch':token} if token else {'IfNoneMatch':'*'}))
            results.append({'source':source,'start':spec['start'],**{k:v for k,v in updated.items() if k not in ('seen','cursor')}})
            break
    report={'at':datetime.now(timezone.utc).isoformat(),'execution_host':'t3','daily_raw':results}
    put(control.s3,'research-data/constellation-backfill/daily-raw/reports/'+uuid.uuid4().hex+'.json',encode(report));print(json.dumps(report),flush=True)

if __name__=='__main__':main()
