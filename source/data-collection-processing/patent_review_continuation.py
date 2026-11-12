"""Bounded patent continuation using existing controller access and source budgets."""
import argparse,fcntl,json,time
from datetime import date,datetime,timezone
from pathlib import Path
from collection_storage import StorageSettings,write_json,now
from research_contract import ROOT,load_json,digest
from cms_coverage_capture import deadline,queue_metadata

def manifests(value):
 if isinstance(value,dict):
  for k,v in value.items():
   if k.endswith('manifest')and isinstance(v,str)and v.startswith('manifests/'):yield v
   else:yield from manifests(v)
 elif isinstance(value,list):
  for v in value:yield from manifests(v)

def run(lane,store,settings):
 if lane=='google':
  from patent_backfill import Backfill
  from patent_bigquery_access import session
  config=load_json(ROOT/'config/patent-backfill-resumed.json');universe=load_json(ROOT/config['universe']);taxonomy=load_json(ROOT/config['taxonomy']);runner=Backfill(store,settings,config,universe,taxonomy)
  with (ROOT/'.patent-backfill.lock').open('a')as lock:
   try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:return {'status':'deferred','reason':'existing_patent_backfill_active'}
   with session(ROOT/config['credentials'])as http:result=runner.run(http)
  return result
 if lane in ('odp','odp-historical'):
  from patent_operations import PatentOperations
  config=load_json(ROOT/'config/patent-operations-resumed.json');runner=PatentOperations(store,settings,config,load_json(ROOT/config['universe']),load_json(ROOT/config['taxonomy']))
  with (ROOT/'.patent-operations.lock').open('a')as lock:
   try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:return {'status':'deferred','reason':'existing_patent_operations_active'}
   return runner.run(['uspto'],'historical',date(2016,1,1),date.fromisoformat(config['daily_origin']),1,0) if lane=='odp-historical' else runner.run(['uspto'],'daily',date.fromisoformat(config['daily_origin']),datetime.now(timezone.utc).date(),1,0)
 raise ValueError('unknown_lane')

def main():
 p=argparse.ArgumentParser();p.add_argument('--lane',choices=['google','odp','odp-historical'],required=True);a=p.parse_args();settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();key='constellation-backfill/patent-reviewed/'+a.lane+'-continuation.json'
 with (ROOT/('state/patent-review-'+a.lane+'.lock')).open('a')as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  prior=store.get(key);state=json.loads(prior.body)if prior else{}
  if state.get('retry_after',0)>time.time():print(json.dumps({'status':'deferred','reason':'source_cooldown','lane':a.lane}),flush=True);return
  try:
   with deadline(150):result=run(a.lane,store,settings)
   for manifest in set(manifests(result)):
    saved=store.get(manifest)
    if saved:queue_metadata(store,json.loads(saved.body))
  except Exception as e:result={'status':'failed','reason':type(e).__name__+': '+str(e)[:250]}
  entry={'lane':a.lane,'result':result,'at':now(),'retry_after':time.time()+(21600 if result.get('status')=='failed'else 120)};write_json(store,key,entry,prior.token if prior else None);write_json(store,'constellation-backfill/patent-reviewed/receipts/'+digest(entry)+'.json',entry);print(json.dumps(entry),flush=True)
if __name__=='__main__':main()
