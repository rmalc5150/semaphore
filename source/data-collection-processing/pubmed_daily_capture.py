"""Bounded independent capture of the configured PubMed topics with durable results."""
import fcntl,json
from datetime import datetime,timezone
from collection_storage import StorageSettings,write_json,now
from research_contract import ROOT,load_json,digest
from specialist_inputs import collect
from specialist_plan import jobs


def main():
 with open('/opt/constellation/tmp/pubmed-daily.lock','a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store()
  universe=load_json(ROOT/'config/drugsfda-inventory-universe.json');plan=load_json(ROOT/'config/specialist-inputs.json')
  plan['sources']=[s for s in plan['sources'] if s['source']=='pubmed_abstracts'];day=datetime.now(timezone.utc).date();results=[]
  for job in jobs(plan,universe,'daily',day):
   identity=digest({'job':job,'universe':digest(universe)})
   try:
    result=collect(job,store,settings,universe,load_json(ROOT/'config/sectors.v1.json'),2)
    if result['status']=='complete':
     manifest=json.loads(store.get(result['manifest']).body)
     if not(manifest['exhausted'] and manifest['status']=='complete'):raise ValueError('uncommitted_pubmed_window')
     key='constellation-backfill/specialist-publication-queue/pubmed-daily/'+identity+'.json'
     if store.get(key) is None:write_json(store,key,{'window_id':identity,'manifests':[result['manifest']],'queued_at':now()})
     result['records']=manifest['record_count']
   except Exception as error:result={'status':'failed','reason':type(error).__name__+': '+str(error)[:300]}
   report={'source':'pubmed_abstracts','job':job,'window_id':identity,'at':now(),**result};results.append(report)
   write_json(store,'constellation-backfill/legacy-operation-receipts/pubmed-daily/'+day.isoformat()+'/'+digest(report)+'.json',report)
   print(json.dumps(report),flush=True)
  if not results or any(r['status']=='failed' for r in results):raise SystemExit(2)
if __name__=='__main__':main()
