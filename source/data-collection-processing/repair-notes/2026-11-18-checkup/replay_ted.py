import os,sys,json,traceback
from pathlib import Path
from datetime import datetime,timezone,timedelta
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
from collection_storage import StorageSettings,write_json,now,Conflict
from research_contract import load_json,digest
from specialist_inputs import collect
settings=StorageSettings.load(root/'config/collection-storage.s3.json');store=settings.store();u=load_json(root/'config/company-universe.v0.5.json');t=load_json(root/'config/sectors.v1.json')
for source in ['ted_notices']:
 started=now();key='constellation-backfill/specialist-schedulers/constellation-specialist-'+source+'.service/historical.json';saved=store.get(key)
 try:
  state=json.loads(saved.body);candidates=[(identity,r) for identity,r in state['jobs'].items() if r.get('status')=='failed'];candidates.sort(key=lambda v:v[1]['job']['start'])
  if not candidates:print(source,'no currently failed scopes',flush=True);continue
  identity,prior=candidates[0];job=prior['job'];assert identity==digest({'job':job,'universe_hash':digest(u),'version':'specialist-inputs-1.2'})
  result=collect(job,store,settings,u,t,2);row={**prior,**result,'last_attempt':now()};row.pop('retry_after',None)
  current=store.get(key);state=json.loads(current.body)
  if state['jobs'][identity].get('last_attempt','')>started:raise Conflict('concurrent scheduler update')
  state['jobs'][identity]=row;state['updated_at']=now();write_json(store,key,state,current.token)
  if result['status']=='complete':
   q='operations/specialists/publication-queue/'+identity+'.json';prev=store.get(q)
   if not prev:write_json(store,q,{'window_id':identity,'manifests':[result['manifest']],'queued_at':now()})
  out={'source':source,'job_id':identity,'start':job['start'],'end':job['end'],**result}
 except Exception as e:out={'source':source,'status':'replay_error','error_type':type(e).__name__}
 write_json(store,'constellation-backfill/repairs/2026-11-18/'+source+'-recovery-'+__import__('uuid').uuid4().hex+'.json',out);print(json.dumps(out),flush=True)
