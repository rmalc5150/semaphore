import json,tempfile
from pathlib import Path
from collection_storage import StorageSettings,write_json,now
from research_contract import load_json,digest
from research_publication import prepare_for
from window_publication import publish_pending
import regulatory_athena
p=Path(__file__).parent;settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();ids=[];manifests=[];checks=[]
entry=json.load(open(p/'fresh-capture.json'));key=entry['manifest'];manifest=json.loads(store.get(key).body);assert manifest['status']=='complete' and manifest['exhausted'];head=json.loads(store.get('checkpoints/'+manifest['task_id']+'/head.json').body);assert key in head['terminal_history'];wid=digest(manifest['task']);qkey='operations/regulatory/publication-queue/'+wid+'.json';old=store.get(qkey)
if old:assert json.loads(old.body)['manifests']==[key]
else:write_json(store,qkey,{'window_id':wid,'manifests':[key],'queued_at':now(),'source':'chictr','dataset':'research_records'})
ids=[wid];manifests=[key];checks=[{'manifest':key,'records':manifest['record_count'],'status':manifest['status']}]
(p/'curated-input-checks.json').write_text(json.dumps(checks,indent=2));print(checks,flush=True)
if not ids:raise SystemExit('No complete/exhausted ChiCTR window available; partial capture retained.')
config=load_json(Path('config/regulatory-athena-pilot.json'));config.pop('source_manifests',None)
with tempfile.TemporaryDirectory(prefix='ctis-publication-')as tmp:
 result=publish_pending(store,settings,'regulatory',config,prepare_for(regulatory_athena),Path(tmp),max_windows=2,window_ids=ids)
(p/'fresh-publication.json').write_text(json.dumps({'manifests':manifests,'window_ids':ids,'result':result},indent=2));print(result,flush=True)
if result['status']=='failed':raise SystemExit(1)
