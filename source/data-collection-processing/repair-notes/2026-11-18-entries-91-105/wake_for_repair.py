from ops import *
code=r'''import json,time,fcntl
from pathlib import Path
from constellation import m7_lifecycle as life,m7_batch as batch
folder=life.STATE.parent;hold=folder/'m7-deployment-hold.json'
with (folder/'m7-lifecycle.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 before={'batch':batch.read(),'hold':json.loads(hold.read_text())if hold.exists()else None}
 if before['hold']and before['hold'].get('expires_at',0)>time.time():raise RuntimeError('An existing deployment hold must be preserved: '+str(before['hold']))
 backup=Path('repair-notes/2026-11-18-entries-91-105/lifecycle-before.json');backup.write_text(json.dumps(before,indent=2)+'\n')
 now=time.time();hold.write_text(json.dumps({'reason':'owner_approved_entries_91_105_repair','created_at':now,'expires_at':now+4*3600})+'\n')
 life.start()
 state=batch.read();state.update(phase='running',started_at=now,wake_reason='owner_approved_entries_91_105_repair',last_checked_at=0);batch.save(state)
 print(json.dumps({'worker':'running_ssm_online','deployment_hold_expires_at':now+4*3600,'batch_payloads':'retain existing batch-paused fence until deployment verified'}))
'''
print(remote(T3,code)['out'])
