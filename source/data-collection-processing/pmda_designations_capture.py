"""Current full SAKIGAKE list capture; this is not an all-drug PMDA route."""
import fcntl,json
from datetime import datetime,timedelta,timezone
from collection_storage import StorageSettings,write_json,now
from research_contract import ROOT,load_json,digest
from regulatory_collection import collect
from regulatory_sources import Japan

def main():
 with open('/opt/constellation/tmp/pmda-designations.lock','a')as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();universe=load_json(ROOT/'config/drugsfda-inventory-universe.json');taxonomy=load_json(ROOT/'config/sectors.v1.json');day=datetime.now(timezone.utc).date()
  result=collect(store,settings,universe,taxonomy,'japan',day,day+timedelta(days=1),'daily',Japan(),max_pages=1)
  assert result['status']=='complete',result
  m=json.loads(store.get(result['manifest']).body);assert m['status']=='complete'and m['exhausted'];ids=[]
  for page in m['pages']:
   for batch in page['batches']:
    ids.extend(json.loads(line)['source_record_id']for line in store.get(batch['key']).body.splitlines())
  assert len(ids)==len(set(ids))==m['record_count']and ids
  wid=digest(m['task']);key='constellation-backfill/specialist-publication-queue/pmda-designations/'+wid+'.json'
  if store.get(key)is None:write_json(store,key,{'window_id':wid,'manifests':[result['manifest']],'queued_at':now()})
  report={'source':'japan_pmda','status':'complete','day':day.isoformat(),'manifest':result['manifest'],'window_id':wid,'records':len(ids),'scope':'Current full SAKIGAKE designation list only; not all Japanese drugs','at':now()};write_json(store,'constellation-backfill/legacy-operation-receipts/pmda-designations/'+day.isoformat()+'/'+digest(report)+'.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':main()
