import json
from pathlib import Path
from collection_storage import StorageSettings
from window_publication import list_keys
p=Path(__file__).parent;settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();out={}
for name,prefix in [('receipts','constellation-backfill/epmc-fulltext/receipts/2026-11-10/'),('outcomes','constellation-backfill/epmc-fulltext/outcomes/'),('windows','constellation-backfill/specialist-publication-queue/epmc-fulltext/')]:
 rows=[json.loads(store.get(k).body)for k in list_keys(store,settings,prefix)];out[name]=rows
 print(name,len(rows),[(r.get('stage'),r.get('status'),r.get('records'),r.get('reason'),r.get('job',{}).get('source'),r.get('job',{}).get('parameters',{}).get('pmcid'))for r in rows][-12:])
(p/'capture-status.json').write_text(json.dumps(out,indent=2))
