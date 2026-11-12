"""One bounded current full Health Canada NOC snapshot per capture day."""
import fcntl,json
from datetime import datetime,timezone
from pathlib import Path
from collection_storage import StorageSettings,write_json,now
from research_contract import ROOT,load_json,digest
from specialist_inputs import collect
from specialist_plan import jobs

def main():
 with open('/opt/constellation/tmp/canada-noc-capture.lock','a')as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  universe=load_json(ROOT/'config/drugsfda-inventory-universe.json');plan=load_json(ROOT/'config/specialist-inputs.json');plan['sources']=[s for s in plan['sources']if s['source']=='canada_noc'];day=datetime.now(timezone.utc).date();planned=list(jobs(plan,universe,'daily',day));assert len(planned)==1;job=planned[0]
  settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();result=collect(job,store,settings,universe,load_json(ROOT/'config/sectors.v1.json'),1)
  if result['status']!='complete':raise RuntimeError('canada_noc_snapshot_incomplete:'+json.dumps(result))
  manifest=json.loads(store.get(result['manifest']).body);assert manifest['exhausted'] and manifest['status']=='complete'
  expected=None;counts={};categories={};unique=set()
  for page in manifest['pages']:
   for batch in page['batches']:
    for line in store.get(batch['key']).body.splitlines():
     record=json.loads(line);data=record['payload']['data'];assert data['noc_number']not in unique;unique.add(data['noc_number']);counts[data.get('noc_active_status','unknown')]=counts.get(data.get('noc_active_status','unknown'),0)+1;categories[data.get('noc_product_type','unknown')]=categories.get(data.get('noc_product_type','unknown'),0)+1
     if expected is None:
      ref=record['payload']['source_evidence'][0];body=json.loads(store.get(ref['key']).body);rows=body if isinstance(body,list) else body.get('data')
      if rows is None:rows=next(v for v in body.values()if isinstance(v,list))
      expected=len(rows)
  assert expected is not None and expected==len(unique)==manifest['record_count']
  identity=digest({'job':job,'universe':digest(universe)});qkey='constellation-backfill/specialist-publication-queue/canada-noc/'+identity+'.json'
  if store.get(qkey)is None:write_json(store,qkey,{'window_id':identity,'manifests':[result['manifest']],'queued_at':now()})
  report={'source':'canada_noc','day':day.isoformat(),'status':'complete','manifest':result['manifest'],'window_id':identity,'provider_rows':expected,'saved_unique_notices':len(unique),'statuses':counts,'categories':categories,'at':now()};write_json(store,'constellation-backfill/legacy-operation-receipts/canada-noc/'+day.isoformat()+'/'+digest(report)+'.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':main()
