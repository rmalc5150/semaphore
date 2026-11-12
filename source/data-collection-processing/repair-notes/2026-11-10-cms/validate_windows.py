import io,json
from pathlib import Path
from collection_storage import StorageSettings
from metadata_engine.evidence import evidence_for
p=Path(__file__).parent;cfg=json.load(open('config/metadata-engine.json'));settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();cache={}
class Reader:
 def get_object(self,**kwargs):
  key=kwargs['Key'];relative=key.removeprefix('research-data/')
  if key not in cache:cache[key]=store.get(relative).body
  return {'Body':io.BytesIO(cache[key]),'ContentLength':len(cache[key])}
reader=Reader();counts={};out=[]
for entry in json.loads((p/'daily-windows.json').read_text()):
 m=json.loads(store.get(entry['manifests'][0]).body);source=m['task']['source'];n=0
 for page in m['pages']:
  for batch in page['batches']:
   for line in store.get(batch['key']).body.splitlines():
    r=json.loads(line);artifacts=evidence_for(r,cfg['contracts'][source],reader,cfg['bucket']);assert artifacts[0]['validation']['provider']=='CMS national coverage';n+=1
 out.append({'source':source,'window_id':entry['window_id'],'verified_records':n});counts[source]=counts.get(source,0)+n
(p/'fresh-batch-validation.json').write_text(json.dumps({'counts':counts,'windows':out},indent=2));print(counts,flush=True)
