import os,sys,json,subprocess
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
from collection_storage import StorageSettings,write_json,now,Conflict
from research_contract import load_json,digest
from specialist_inputs import collect
settings=StorageSettings.load(root/'config/collection-storage.s3.json');store=settings.store();u=load_json(root/'config/company-universe.v0.5.json');t=load_json(root/'config/sectors.v1.json')
key='operations/specialists/scheduler/daily.json';saved=store.get(key);state=json.loads(saved.body);identity='ff8ccfcba6ce16e7c0716a5c76dde8109278915e39376fc2c6a661589f6aa429';prior=state['jobs'][identity];job=prior['job'];started=now()
try:
 result=collect(job,store,settings,u,t,2);row={**prior,**result,'last_attempt':now()};row.pop('retry_after',None)
 current=store.get(key);state=json.loads(current.body)
 if state['jobs'][identity].get('last_attempt','')>started:raise Conflict('concurrent scheduler update')
 state['jobs'][identity]=row;state['updated_at']=now();write_json(store,key,state,current.token)
 if result['status']=='complete':
  q='operations/specialists/publication-queue/'+identity+'.json';prev=store.get(q);write_json(store,q,{'window_id':identity,'manifests':[result['manifest']],'queued_at':now()},prev.token if prev else None)
except Exception as e:result={'status':'repair_failed','error_type':type(e).__name__,'reason':str(e)[:500]}
write_json(store,'constellation-backfill/repairs/2026-11-16-afternoon/eia-replay.json',result);print('EIA',json.dumps(result),flush=True)
for line in subprocess.run(['systemctl','list-unit-files','--no-pager'],capture_output=True,text=True).stdout.splitlines():
 if any(s in line for s in ['news-collection','fda-reference','product-code']):print('UNIT',line)
