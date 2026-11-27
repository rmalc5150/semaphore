import os,sys,json
from pathlib import Path
from datetime import date
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
from collection_storage import StorageSettings,write_json
import patent_prosecution as p
settings=StorageSettings.load(root/'config/collection-storage.s3.json');store=settings.store()
k='manifests/collection_runs/source=uspto_odp/dataset=patent_office_actions/run_8eda8df5-8573-4e50-a449-8889460e8ed1/final.json';task=json.loads(store.get(k).body)['task'];u=json.loads(store.get('manifests/configurations/universe/'+task['universe_hash']+'.json').body);t=json.loads(store.get('manifests/configurations/taxonomy/'+task['taxonomy_hash']+'.json').body)
r=p.collect(store,settings,u,t,task['dataset'],date.fromisoformat(task['window']['start'][:10]),date.fromisoformat(task['window']['end'][:10]),mode=task['mode'],page_size=task['scope']['page_size'],max_pages=1,client=p.Client(store,max_requests=12,max_download_bytes=16*1024**2),lane=task['scope']['lane'])
print(json.dumps(r));write_json(store,'constellation-backfill/repairs/2026-11-16-afternoon/patent-bounded-replay.json',r)
