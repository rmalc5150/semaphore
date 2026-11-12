"""Bounded CMS catalog refresh and resumed financial-file ingestion; no messaging."""
import argparse,fcntl,json,time,sqlite3,tempfile,hashlib
from pathlib import Path
from datetime import datetime,timezone
from collection_storage import StorageSettings,write_json,now
from research_contract import ROOT,load_json,digest
from specialist_inputs import collect
from specialist_plan import jobs
from cms_coverage_capture import queue_metadata,deadline
from cms_financial_collection import execute,TABLES,registry
BASE='constellation-backfill/cms-payments/'
PUBLICATION='constellation-backfill/specialist-publication-queue/cms-payments/'

def save(store,key,value):
 old=store.get(key);write_json(store,key,value,old.token if old else None)

def catalog(store,settings):
 day=datetime.now(timezone.utc).date();key=BASE+'catalog-state.json';obj=store.get(key);state=json.loads(obj.body)if obj else{}
 if state.get('day')==day.isoformat()and(state.get('status')=='complete'or state.get('retry_after',0)>time.time()):return
 plan=load_json(ROOT/'config/specialist-inputs.json');plan['sources']=[s for s in plan['sources']if s['source']=='cms_payments_catalog'];universe=load_json(ROOT/'config/drugsfda-inventory-universe.json');taxonomy=load_json(ROOT/'config/sectors.v1.json')
 for job in jobs(plan,universe,'daily',day):
  try:
   with deadline(75):result=collect(job,store,settings,universe,taxonomy,1)
   if result.get('status')=='complete':
    m=json.loads(store.get(result['manifest']).body)
    if m['status']!='complete'or not m['exhausted']:raise ValueError('cms_catalog_uncommitted_manifest')
    identity=digest({'job':job,'manifest':result['manifest']});target=PUBLICATION+identity+'.json'
    if store.get(target)is None:write_json(store,target,{'window_id':identity,'manifests':[result['manifest']],'queued_at':now()})
    queue_metadata(store,m);result.update(records=m['record_count'],window_id=identity)
  except Exception as error:result={'status':'failed','reason':type(error).__name__+': '+str(error)[:300]}
  state={'day':day.isoformat(),'at':now(),**result,'retry_after':time.time()+900};save(store,key,state);write_json(store,BASE+'receipts/catalog/'+digest(state)+'.json',state);print(json.dumps({'catalog':state}),flush=True)

def verify_done(db,config,store):
 import boto3
 from committed_data_athena import query
 rows=db.execute("SELECT meta,state FROM editions WHERE status='done'").fetchall();expected={json.loads(m)['edition_id']:json.loads(s)['row_count']for m,s in rows};actual={}
 a=boto3.client('athena',region_name=config['region'])
 for source,table in TABLES.items():
  ids=[json.loads(m)['edition_id']for m,_ in rows if json.loads(m)['source']==source]
  if not ids:continue
  clause=','.join("'"+i+"'"for i in ids)
  result=query(a,f"SELECT edition_id,count(*) FROM {config['athena_database']}.{table} WHERE edition_id IN ({clause}) GROUP BY edition_id")
  actual.update({r[0]:int(r[1])for r in result['rows']})
 if actual!=expected:raise ValueError('cms_financial_athena_count_mismatch')
 for meta_raw,state_raw in rows:
  state=json.loads(state_raw);m=json.loads(store.client.get_object(Bucket=store.bucket,Key=state['manifest_key'])['Body'].read())
  if m.get('sha256')!=state['sha256']or m.get('row_count')!=state['row_count']:raise ValueError('cms_financial_manifest_mismatch')
  head=store.client.head_object(Bucket=store.bucket,Key=state['raw_key'])
  if head['ContentLength']!=state['total_bytes']:raise ValueError('cms_financial_raw_size_mismatch')
 receipt={'status':'verified','verified_at':now(),'edition_counts':actual,'verification_scope':'exact Athena row counts versus committed CSV checkpoints, original checksum receipts and archived file sizes; no full-file rehash or unique-ID rescan'}
 key=BASE+'verification/'+digest(receipt)+'.json'
 write_json(store,key,receipt)
 receipt.update(verification_key=key,verification_sha256=hashlib.sha256(store.get(key).body).hexdigest())
 save(store,BASE+'verification/latest.json',receipt);return receipt

def backup(config,store):
 state=Path(config['state_file'])
 with tempfile.TemporaryDirectory(prefix='cms-state-backup-')as tmp:
  target=Path(tmp)/'registry.sqlite3'
  with sqlite3.connect(state)as source,sqlite3.connect(target)as dest:source.backup(dest)
  raw=target.read_bytes();sha=hashlib.sha256(raw).hexdigest();key=BASE+'registry/'+sha+'.sqlite3'
  if store.get(key)is None:store.put(key,raw,content_type='application/vnd.sqlite3')
  save(store,BASE+'registry/latest.json',{'key':key,'sha256':sha,'bytes':len(raw),'at':now()})

def main():
 import csv
 csv.field_size_limit(16*1024*1024)
 parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=('catalog','financial','all'),default='all');parser.add_argument('--config',default='config/cms-financial-resumed.json');args=parser.parse_args()
 config=load_json(ROOT/args.config)
 lock_path=Path(config['state_file']).parent/'capture.lock' if args.mode=='financial' else Path('/opt/constellation/tmp/cms-payments-resumed.lock')
 with open(lock_path,'a')as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store()
  if args.mode in ('catalog','all'):catalog(store,settings)
  if args.mode=='catalog':return
  try:
   status=execute(config);print(json.dumps({'financial_status':[(e['title'],e['status'],e.get('error'))for e in status['editions']]}),flush=True)
   old=store.get(BASE+'verification/latest.json');receipt=json.loads(old.body)if old else{}
   if not receipt or not receipt.get('verification_key') or time.time()-datetime.fromisoformat(receipt['verified_at'].replace('Z','+00:00')).timestamp()>86400:
    with registry(config['state_file'])as db:print(json.dumps({'financial_verification':verify_done(db,config,store)}),flush=True)
  finally:backup(config,store)
if __name__=='__main__':main()
