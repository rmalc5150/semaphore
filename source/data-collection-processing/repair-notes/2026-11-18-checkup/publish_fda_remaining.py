import os,sys,json,fcntl,time
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
from collection_storage import StorageSettings,write_json,now
from research_contract import load_json
from window_publication import publish_pending
from regulatory_athena import prepare
settings=StorageSettings.load(root/'config/collection-storage.s3.json');store=settings.store();config=load_json(root/'config/regulatory-athena-pilot.json')
proof=json.loads(store.get('constellation-backfill/repairs/2026-11-16-afternoon/monitoring-reconciliation.json').body);ids=[r['task_id'][5:] for r in proof['fda_windows']]
def build(store,settings,config,manifests,out):return prepare(store,settings,{**config,'source_manifests':manifests},out)
results=[]
for offset in range(0,len(ids),3):
 with Path('/opt/constellation/auxiliary-publication/publish.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  r=publish_pending(store,settings,'regulatory',config,build,root/'regulatory-checkup1118-build',max_windows=3,window_ids=ids[offset:offset+3]);results.append(r)
  write_json(store,'constellation-backfill/repairs/2026-11-18/fda-publication-'+str(offset)+'.json',{'at':now(),'result':r});print(json.dumps({'offset':offset,'result':r}),flush=True)
 time.sleep(2)
