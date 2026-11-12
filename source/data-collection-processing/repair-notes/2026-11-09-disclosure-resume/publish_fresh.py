import json,tempfile
from pathlib import Path
from collection_storage import StorageSettings,write_json,now
from research_contract import load_json,digest
from research_publication import prepare_for
from window_publication import publish_pending
import disclosure_athena
p=Path(__file__).parent;settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();key='operations/s11-content/daily/f8e1bc75867c6a0a99edb6e3859b37e052424fabdf986f7181cc7ee1b4eef231/state.json';state=json.loads(store.get(key).body);ids=[];manifests=[]
for stage,entry in state.get('stages',{}).items():
 if stage not in ('documents','press-releases','licensing-agreements','ma-announcements','strategic-transactions') or entry.get('status')!='complete':continue
 manifest=json.loads(store.get(entry['manifest']).body);assert manifest['status']=='complete'and manifest['exhausted'];wid=digest(manifest['task']);head=json.loads(store.get('checkpoints/'+manifest['task_id']+'/head.json').body);assert entry['manifest']in head['terminal_history'];qkey='operations/disclosures/publication-queue/'+wid+'.json';old=store.get(qkey)
 if old:assert json.loads(old.body)['manifests']==[entry['manifest']]
 else:write_json(store,qkey,{'window_id':wid,'manifests':[entry['manifest']],'queued_at':now(),'source':manifest['task']['source'],'dataset':manifest['task']['dataset']})
 ids.append(wid);manifests.append(entry['manifest'])
assert ids
config=load_json(Path('config/disclosure-athena-pilot.json'));config.pop('source_manifests',None)
with tempfile.TemporaryDirectory(prefix='disclosure-publication-')as tmp:
 result=publish_pending(store,settings,'disclosures',config,prepare_for(disclosure_athena),Path(tmp),max_windows=5,window_ids=ids)
(p/'fresh-publication.json').write_text(json.dumps({'manifests':manifests,'window_ids':ids,'result':result},indent=2));print(json.dumps(result),flush=True)
if result['status']=='failed':raise SystemExit(1)
