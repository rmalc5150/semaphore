import json
from pathlib import Path
from collection_storage import StorageSettings
from window_publication import list_keys
p=Path(__file__).parent;settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();rows=[]
for key in list_keys(store,settings,'constellation-backfill/conferences-resumed/receipts/2026-11-10/'):
 r=json.loads(store.get(key).body)
 if r.get('manifest'):
  m=json.loads(store.get(r['manifest']).body);r.update(saved_records=m['record_count'],pages=len(m['pages']),resumed_from_run_id=m.get('resumed_from_run_id'),exhausted=m.get('exhausted'))
 rows.append(r)
rows.sort(key=lambda r:r['at']);(p/'capture-status.json').write_text(json.dumps(rows,indent=2));print([{k:r.get(k)for k in ['mode','day','status','reason','saved_records','pages','resumed_from_run_id','exhausted']}for r in rows][-7:])
