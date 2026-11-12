import json
from pathlib import Path
from collection_storage import StorageSettings
from window_publication import list_keys
from metadata_engine.runtime_db import Database
p=Path(__file__).parent;settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();out={}
for name in ('discovery-state','capture-state'):
 obj=store.get('constellation-backfill/cms-coverage/'+name+'.json');out[name]=json.loads(obj.body)if obj else None
for name,prefix in [('outcomes','constellation-backfill/cms-coverage/outcomes/'),('windows','constellation-backfill/specialist-publication-queue/cms-coverage/')]:
 keys=list_keys(store,settings,prefix);out[name]=[json.loads(store.get(k).body)for k in keys[:40]]
db=Database(json.load(open('config/metadata-engine.json')))
with db.tx()as c:
 c.execute("SELECT source_key,state,count(*) n FROM engine_jobs WHERE source_key IN ('cms_coverage','cms_coverage_documents') GROUP BY source_key,state");out['jobs']=c.fetchall()
 c.execute("SELECT * FROM engine_sources WHERE source_key IN ('cms_coverage','cms_coverage_documents')");out['sources']=c.fetchall()
(p/'capture-status.json').write_text(json.dumps(out,indent=2,default=str));print(json.dumps({'sources':out['sources'],'jobs':out['jobs'],'parent_outcomes':[(v['job']['parameters'],v['status'],v.get('reason'))for v in (out.get('discovery-state')or{}).get('parents',{}).values()],'document_outcomes':[(v['job']['parameters'],v['status'],v.get('reason'))for v in out['outcomes']],'publication_windows':len(out['windows'])},default=str))
