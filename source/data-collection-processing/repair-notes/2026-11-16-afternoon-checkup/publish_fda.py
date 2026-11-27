import os,sys,json,fcntl,time
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
from collection_storage import StorageSettings,write_json,now
from research_contract import load_json
from window_publication import publish_pending
from regulatory_athena import prepare
settings=StorageSettings.load(root/'config/collection-storage.s3.json');store=settings.store();config=load_json(root/'config/regulatory-athena-pilot.json');ids=[]
for month in [2,3,4]:
 obj=store.get('constellation-backfill/repairs/2026-11-16-afternoon/core-fda-2016-'+str(month).zfill(2)+'-01.json');r=json.loads(obj.body)
 if r.get('status')=='complete':ids.append(r['window_id'])
def build(store,settings,config,manifests,out):return prepare(store,settings,{**config,'source_manifests':manifests},out)
with Path('/opt/constellation/auxiliary-publication/publish.lock').open('a') as lock:
 for attempt in range(25):
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
  except BlockingIOError:
   if attempt==24:raise RuntimeError('publication lock busy; exact windows remain queued')
   time.sleep(5)
 r=publish_pending(store,settings,'regulatory',config,build,root/'regulatory-afternoon-repair-build',max_windows=len(ids),window_ids=ids)
write_json(store,'constellation-backfill/repairs/2026-11-16-afternoon/fda-publication.json',{'at':now(),'result':r});print(json.dumps(r),flush=True)
