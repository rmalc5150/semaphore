import json,fcntl,sys
from datetime import datetime
from zoneinfo import ZoneInfo
from collection_storage import StorageSettings
from research_contract import ROOT,load_json
from disclosure_collection import collect_hkex
s=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=s.store()
m=json.loads(store.get(sys.argv[1]).body);t=m['task'];scope=t['scope'];u=json.loads(store.get('manifests/configurations/universe/'+t['universe_hash']+'.json').body);tax=json.loads(store.get('manifests/configurations/taxonomy/'+t['taxonomy_hash']+'.json').body)
a,b=[datetime.fromisoformat(t['window'][k].replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Hong_Kong')).date() for k in ('start','end')]
with (ROOT/'.collection-operations.lock').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
 r=collect_hkex(store,s,u,tax,a,b,t['mode'],scope['selection'],scope['sectors'],scope['stock_id'],scope['page_size'],max_pages=1)
 print(json.dumps({'replayed':sys.argv[1],**r}),flush=True)
 if r['status']=='failed':raise SystemExit(2)
