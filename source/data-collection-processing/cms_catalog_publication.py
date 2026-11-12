"""Publish bounded CMS source windows using the existing specialist contract."""
import fcntl,json,tempfile
from pathlib import Path
from collection_storage import StorageSettings,write_json
from research_contract import ROOT,load_json
from specialist_publication import publication_config
from window_publication import list_keys,publish_pending
from source_observation_athena import prepare

def main():
 with (ROOT/'.specialist-publication.lock').open('a')as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:
   print(json.dumps({'status':'deferred','reason':'specialist_publication_active'}),flush=True);return 0
  settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();ids=[]
  keys=[]
  for folder in ('cms-payments',):
   keys.extend(list_keys(store,settings,'constellation-backfill/specialist-publication-queue/'+folder+'/'))
  for key in keys:
   entry=json.loads(store.get(key).body);target='operations/specialists/publication-queue/'+entry['window_id']+'.json';prior=store.get(target)
   if prior:
    if json.loads(prior.body)['manifests']!=entry['manifests']:raise ValueError('cms_publication_manifest_conflict')
   else:write_json(store,target,entry)
   ids.append(entry['window_id'])
  config=publication_config(settings,load_json(ROOT/'config/specialist-inputs.json'))
  def build(s,settings,config,manifests,root):return prepare(s,settings,{**config,'source_manifests':manifests},root)
  with tempfile.TemporaryDirectory(prefix='cms-catalog-publication-')as tmp:result=publish_pending(store,settings,'specialists',config,build,Path(tmp),max_windows=1,window_ids=ids)
  print(json.dumps(result),flush=True);return int(result['status']=='failed')
if __name__=='__main__':raise SystemExit(main())
