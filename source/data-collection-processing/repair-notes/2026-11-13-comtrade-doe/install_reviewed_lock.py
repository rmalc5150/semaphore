"""Give the bounded metadata pass its own lock; preserve active payloads."""
import contextlib,io,json
from pathlib import Path
from constellation.finish_aux_migration import remote,M7

CODE='''import json,subprocess,os,time,boto3
from pathlib import Path
unit='optima-m7-aux-reviewed-metadata-publication.service'
pid=int(subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True))
waiting=False
if pid:
 p=Path('/proc')/str(pid)
 waiting=((p/'comm').read_text().strip()=='flock' and not(p/'task'/str(pid)/'children').read_text().strip()
          and(p/'wchan').read_text().strip()=='locks_lock_inode_wait')
drop=Path('/etc/systemd/system/'+unit+'.d/zzzzzz-reviewed-publication-lock.conf');drop.parent.mkdir(exist_ok=True)
body='[Service]\\nExecStart=\\nExecStart=/usr/bin/flock /opt/constellation/auxiliary-publication/reviewed-metadata.lock /opt/constellation/legacy-venv/bin/python -B reviewed_metadata_publication.py\\n'
if drop.exists():assert drop.read_text()==body
drop.write_text(body)
lock=Path('/opt/constellation/auxiliary-publication/reviewed-metadata.lock');lock.touch();os.chown(lock,1000,1000)
subprocess.run(['systemctl','daemon-reload'],check=True)
if waiting:subprocess.run(['systemctl','stop',unit],check=True)
subprocess.run(['systemctl','start','--no-block',unit],check=True)
out={'installed_at_epoch':time.time(),'unit':unit,'previous_pid':pid,'cancelled_lock_waiter_only':waiting,'dropin':str(drop),'content':body}
key='research-data/constellation-backfill/repairs/comtrade-doe-20261113/reviewed-lock-deployment.json'
boto3.client('s3',region_name='us-east-1').put_object(Bucket='data-collection-059416028963-us-east-1-an',Key=key,Body=json.dumps(out).encode(),ServerSideEncryption='AES256')
print(json.dumps(out))
'''
cap=io.StringIO()
with contextlib.redirect_stdout(cap):remote(M7,CODE)
r=json.loads(cap.getvalue());assert r['status']=='Success',r
Path(__file__).with_name('reviewed-lock-command.json').write_text(json.dumps(r,indent=2)+'\n')
print(r['out'])
