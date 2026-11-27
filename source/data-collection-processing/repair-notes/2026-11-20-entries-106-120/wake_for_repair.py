"""Run the approved repair on C7 under a bounded lifecycle hold."""
import argparse
from ops import T3, remote

parser = argparse.ArgumentParser()
parser.add_argument('action', choices=('wake', 'release'))
action = parser.parse_args().action

code = r'''
import fcntl
import json
from pathlib import Path
import subprocess
import time

from constellation import m7_batch as batch, m7_lifecycle as lifecycle

repair = Path('repair-notes/2026-11-20-entries-106-120')
folder = lifecycle.STATE.parent
hold = folder/'m7-deployment-hold.json'
reason = 'owner_approved_entries_106_120_repair'
with (folder/'m7-lifecycle.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    existing = json.loads(hold.read_text()) if hold.exists() else None
    if ACTION == 'release':
        if existing and existing.get('reason') == reason:
            hold.unlink()
        print(json.dumps({'released': not hold.exists(), 'batch_phase': batch.read()['phase']}))
    else:
        now = time.time()
        if existing and existing.get('expires_at',0)>now and existing.get('reason')!=reason:
            raise RuntimeError('Existing lifecycle hold belongs to another deployment')
        backup = repair/'lifecycle-before.json'
        state = batch.read()
        if not backup.exists():
            backup.write_text(json.dumps({'batch':state,'hold':existing},indent=2)+'\n')
        hold_data = {'reason':reason,'created_at':now,'expires_at':now+8100}
        temporary = hold.with_suffix('.tmp')
        temporary.write_text(json.dumps(hold_data)+'\n')
        temporary.replace(hold)
        lifecycle.start()
        if state['phase'] not in ('running','catchup'):
            state.update(phase='running',started_at=now,wake_reason=reason,last_checked_at=0)
            batch.save(state)
        proof = batch.remote_control('resume')
        state = batch.read()
        state['last_checked_at'] = time.time()
        batch.save(state)
        print(json.dumps({'phase':state['phase'],'expires_at':hold_data['expires_at'],'resume':proof}))
if ACTION == 'wake':
    subprocess.run(['systemctl','start','--no-block','optima-source-review-106-120.service'],check=True)
'''.replace('ACTION', repr(action))

print(remote(T3,code)['out'])
