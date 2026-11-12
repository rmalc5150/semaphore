import json,fcntl
from datetime import datetime,timezone
from collection_storage import StorageSettings
from research_contract import ROOT,load_json
from patent_prosecution_operations import Operations
p=ROOT/'repair-notes/2026-10-23-uspto-exception'
cfg=load_json(ROOT/'config/patent-prosecution-operations.json');cfg.update(max_pages=1,max_windows=1)
s=StorageSettings.load(ROOT/cfg['storage_config']);store=s.store()
with (ROOT/'.patent-prosecution.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 ops=Operations(store,s,cfg,load_json(ROOT/cfg['universe']),load_json(ROOT/cfg['taxonomy']))
 result=ops.run('patent_office_actions','historical',datetime.now(timezone.utc).date())
 print(json.dumps(result),flush=True)
 for r in result.get('windows',[]):
  if r.get('reason') not in (None,'page_limit'):raise RuntimeError('Replay remains blocked: '+str(r))
