import os,sys,json,subprocess
from pathlib import Path
from datetime import date
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
from collection_storage import StorageSettings,write_json
from research_contract import load_json
from collection_operations import Operations
settings=StorageSettings.load(root/'config/collection-storage.s3.json');store=settings.store();cfg=load_json(root/'config/constellation-core-public.json');cfg['max_pages']=30
op=Operations(store,settings,cfg,load_json(root/cfg['universe']),load_json(root/cfg['taxonomy']))
r=op.window('clinicaltrials',date(2022,8,1),date(2022,9,1),'historical');write_json(store,'constellation-backfill/repairs/2026-11-18/clinicaltrials-'+__import__('uuid').uuid4().hex+'.json',r);print(json.dumps(r),flush=True)

if r['status']=='complete':
 from research_contract import digest
 from collection_storage import now
 m=json.loads(store.get(r['manifest']).body);wid=digest(m['task']);q='operations/regulatory/publication-queue/'+wid+'.json';prior=store.get(q)
 if not prior:write_json(store,q,{'window_id':wid,'manifests':[r['manifest']],'queued_at':now(),'source':'clinicaltrials_gov','dataset':'research_records'})
 print('QUEUED',wid,flush=True)
