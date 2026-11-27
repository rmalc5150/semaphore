import json,fcntl
from pathlib import Path
from research_contract import ROOT,load_json
from collection_storage import StorageSettings,write_json,now,Conflict
from specialist_inputs import collect
with (ROOT/'.authenticated-job.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();key='operations/specialists/scheduler/authenticated-daily.json';start=now();saved=store.get(key);state=json.loads(saved.body);identity='423b5bfc823333c16c0bacf6bcf1faff77f1159f1bc88e17e523a9cbb8dfa5e9';prior=state['jobs'][identity];job=prior['job']
 r=collect(job,store,settings,load_json(ROOT/'config/company-universe.v0.5.json'),load_json(ROOT/'config/sectors.v1.json'),5)
 current=store.get(key);state=json.loads(current.body)
 if state['jobs'][identity].get('last_attempt','')>start:raise Conflict('concurrent scheduler update')
 state['jobs'][identity]={**prior,**r,'last_attempt':now()};state['updated_at']=now()
 if r['status']!='failed':state['jobs'][identity].pop('retry_after',None)
 write_json(store,key,state,current.token)
 if r['status']=='complete':
  q='operations/specialists/publication-queue/'+identity+'.json';prev=store.get(q);write_json(store,q,{'window_id':identity,'manifests':[r['manifest']],'queued_at':now()},prev.token if prev else None)
 write_json(store,'constellation-backfill/repairs/2026-11-23/sam-replay.json',r);print(json.dumps(r),flush=True)
