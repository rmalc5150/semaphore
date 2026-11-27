from ops import *
code=r'''import json,time,fcntl,subprocess,boto3
from pathlib import Path
from constellation import m7_lifecycle as life,m7_batch as batch
expected=json.load(open('repair-notes/2026-11-18-entries-91-105/controller-check.json'))['batch_policy'];assert batch.policy()==expected,'Preserve the owner batch policy'
with (life.STATE.parent/'m7-lifecycle.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);hold=life.STATE.parent/'m7-deployment-hold.json';value=json.loads(hold.read_text());assert value['reason']=='owner_approved_entries_91_105_repair'
 before=json.load(open('repair-notes/2026-11-18-entries-91-105/lifecycle-before.json'))
 if before['hold']is None:hold.unlink()
 else:hold.write_text(json.dumps(before['hold'])+'\n')
 assert not life.deployment_hold_active();state=batch.read()
assert subprocess.run(['systemctl','is-active','--quiet','optima-m7-shared-autostop.timer']).returncode==0
subprocess.run(['systemctl','start','--no-block','optima-m7-shared-autostop.service'],check=True)
out={'checked_at':time.time(),'deployment_hold_active':False,'batch_phase':state['phase'],'started_at':state.get('started_at'),'policy_unchanged':batch.policy()==expected,'policy':batch.policy(),'shared_autostop_timer':'active','normal_lifecycle_check':'requested'}
boto3.client('s3',region_name='us-east-1').put_object(Bucket=BUCKET,Key=BASE+'lifecycle-final.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print(json.dumps(out))
'''.replace('BUCKET',repr(B)).replace('BASE',repr(BASE))
r=remote(T3,code);print(r['out']);(P/'lifecycle-final.json').write_text(r['out'])
