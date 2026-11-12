import json,fcntl
from pathlib import Path
from collection_storage import StorageSettings,write_json,now
from research_contract import ROOT,load_json
from market_athena import prepare
from window_publication import publish_pending
p=ROOT/'repair-notes/2026-10-21-market-coverage'
events=[json.loads(x) for x in (p/'mapping-replay.log').read_text().splitlines() if x.startswith('{')]
ids=next(x['window_ids'] for x in events if x.get('stage')=='market_mapping_publication')
s=StorageSettings.load(ROOT/'config/collection-storage.s3.json')
with (ROOT/'.market-athena.lock').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
 for wid in ids:
  key='operations/market/publication-retries/'+wid+'.json';old=s.store().get(key)
  if old:
   d=json.loads(old.body);d['retry_after']=now();write_json(s.store(),key,d,old.token)
 r=publish_pending(s.store(),s,'market',load_json(ROOT/'config/market-athena.json'),prepare,Path('/tmp/optima-market-repair-build'),max_windows=4,window_ids=ids)
 print(json.dumps(r),flush=True)
 if r['status']=='failed':raise SystemExit(2)
