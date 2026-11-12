"""Bounded all-application inventory, independent of dated source backfill."""
import fcntl,hashlib,json,tempfile
from datetime import datetime,timezone
from pathlib import Path
import boto3
from research_contract import ROOT,digest,load_json
from collection_storage import StorageSettings,write_json,now
from specialist_plan import jobs
from specialist_inputs import collect

def main():
 with open('/opt/constellation/tmp/drugsfda-inventory.lock','a')as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  s=boto3.client('s3',region_name='us-east-1');bucket='data-collection-059416028963-us-east-1-an'
  universe=load_json(ROOT/'config/drugsfda-inventory-universe.json')
  plan=load_json(ROOT/'config/specialist-inputs.json');plan['sources']=[r for r in plan['sources']if r['source']=='drugsfda_applications'];plan['sources'][0]['full_inventory']=True;plan['sources'][0].pop('inventory_execution',None)
  today=datetime.now(timezone.utc).date();scopes=[j for j in jobs(plan,universe,'daily',today)if j['parameters'].get('inventory_scope')]
  store_settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=store_settings.store();key='constellation-backfill/specialist-schedulers/drugsfda-inventory/state.json';prior=store.get(key);state=json.loads(prior.body)if prior else {'jobs':{}};out=[]
  for j in scopes:
   identity=digest({'job':j,'universe':digest(universe)})
   if state['jobs'].get(identity,{}).get('status')=='complete':continue
   result=collect(j,store,store_settings,universe,load_json(ROOT/'config/sectors.v1.json'),4)
   state['jobs'][identity]={'partition':j['parameters']['partition'],'updated_at':now(),**result};out.append(state['jobs'][identity])
   if result['status']=='complete':
    qkey='constellation-backfill/specialist-publication-queue/drugsfda-inventory/'+identity+'.json'
    if store.get(qkey)is None:write_json(store,qkey,{'window_id':identity,'manifests':[result['manifest']],'queued_at':now()})
   if len(out)>=2:break
  state.update(updated_at=now(),current_scope_count=len(scopes),scope='All current Drugs@FDA provider applications; not historical vintages',outcomes=out)
  write_json(store,key,state,prior.token if prior else None);print(json.dumps(state),flush=True)
if __name__=='__main__':main()
