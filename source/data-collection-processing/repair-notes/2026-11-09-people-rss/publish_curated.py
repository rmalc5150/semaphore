import json,tempfile
from pathlib import Path
from collection_storage import StorageSettings,write_json,now
from research_contract import load_json,digest
from research_publication import prepare_for
from window_publication import publish_pending
import source_observation_athena
p=Path(__file__).parent;settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();ids=[];manifests=[]
for entry in json.loads((p/'live-captures.json').read_text()):
 if entry['capture']['status']!='captured':continue
 key=entry['manifest'];manifest=json.loads(store.get(key).body);wid=digest(manifest['task']);assert manifest['status']=='complete' and manifest['exhausted'];qkey='operations/people/publication-queue/'+wid+'.json';old=store.get(qkey)
 if old:assert json.loads(old.body)['manifests']==[key]
 else:write_json(store,qkey,{'window_id':wid,'manifests':[key],'queued_at':now(),'source':'people_rss','dataset':'people_source_records'})
 ids.append(wid);manifests.append(key)
assert ids
config=load_json(Path('config/people-observations-athena.json'));config.pop('source_manifests',None)
with tempfile.TemporaryDirectory(prefix='disclosure-publication-')as tmp:
 result=publish_pending(store,settings,'people',config,prepare_for(source_observation_athena),Path(tmp),max_windows=5,window_ids=ids)
(p/'fresh-publication.json').write_text(json.dumps({'manifests':manifests,'window_ids':ids,'result':result},indent=2));print(json.dumps(result),flush=True)
if result['status']=='failed':raise SystemExit(1)
