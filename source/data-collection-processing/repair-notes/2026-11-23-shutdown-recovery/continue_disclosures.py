import os,sys,json
from pathlib import Path
from datetime import date,timedelta
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
from collection_storage import StorageSettings,write_json,now
from research_contract import load_json,digest
from collection_operations import Operations
settings=StorageSettings.load(root/'config/collection-storage.s3.json');store=settings.store();cfg=load_json(root/'config/constellation-core-public.json');cfg['max_records']=2000;cfg['max_pages']=3
op=Operations(store,settings,cfg,load_json(root/cfg['universe']),load_json(root/cfg['taxonomy']));assert op.identity=='935af362e43726fe97e95f4c6848b591ce8083c6cdf1ec5843bef67f9ae9d53f'
for day in [date(2026,10,14)]:
 for source in ['documents','press-releases','licensing-agreements','ma-announcements','strategic-transactions']:
  r=op.window(source,day,day+timedelta(days=1),'daily');out={k:r.get(k)for k in ['source','status','reason','manifest','records']}
  if r['status']=='complete':
   m=json.loads(store.get(r['manifest']).body);wid=digest(m['task']);q='operations/disclosures/publication-queue/'+wid+'.json';prev=store.get(q)
   if not prev or json.loads(prev.body)['manifests']!=[r['manifest']]:write_json(store,q,{'window_id':wid,'manifests':[r['manifest']],'queued_at':now()},prev.token if prev else None)
   out['window_id']=wid
  key='constellation-backfill/repairs/2026-11-23/disclosures-'+str(day)+'-'+source+'.json'; prior=store.get(key); write_json(store,key,out,prior.token if prior else None);print(json.dumps({'day':str(day),**out}),flush=True)
  if r['status']!='complete':break
