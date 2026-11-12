"""Stage final document workers; cut over only after scoped access is verified."""
import base64,json,hashlib
from pathlib import Path
from constellation.finish_aux_migration import remote,M7,T3,ROOT,session

NAMES=['federal-register-daily-enrichment','nist-robotics-daily']
TARGET='/opt/constellation/capture-workers/source'

def stage():
 for name in ['constellation/m7_capture_plan.py','federal_register_daily.py','federal_register_enrichment.py','nist_robotics_pipeline.py','nist_robotics.py','config/nist-robotics.json']:
  payload=base64.b64encode((ROOT/name).read_bytes()).decode()
  remote(M7,"""from pathlib import Path
import base64,os
p=Path(TARGET)/NAME;tmp=p.with_suffix('.document-stage');tmp.write_bytes(base64.b64decode(PAYLOAD));os.chown(tmp,1000,1000);tmp.replace(p);print('Staged',NAME)
""".replace('TARGET',repr(TARGET)).replace('NAME',repr(name)).replace('PAYLOAD',repr(payload)))
 remote(M7,"""from pathlib import Path
import subprocess,os
template=Path('/etc/systemd/system/optima-m7-capture-eodhd-profiles.service').read_text()
for name in NAMES:
 unit='optima-m7-capture-'+name+'.service';old='optima-m7-capture-eodhd-profiles.service'
 text=template.replace('eodhd-profiles',name)
 Path('/etc/systemd/system/'+unit).write_text(text)
 tmp=Path('/opt/constellation/tmp/publication-staging')/unit;tmp.mkdir(exist_ok=True);os.chown(tmp,1000,1000)
subprocess.run(['systemctl','daemon-reload'],check=True);subprocess.run(['systemd-analyze','verify',*['optima-m7-capture-'+n+'.service'for n in NAMES]],check=True)
print('Two final document worker units staged; existing t3 schedules remain active')
""".replace('NAMES',repr(NAMES)))

def cutover():
 remote(M7,"""import boto3
s=boto3.client('s3',region_name='us-east-1')
for prefix in ['operations/federal-register/','operations/nist-robotics/']:
 key='research-data/'+prefix+'worker-permission-check-2026-11-12.json'
 s.put_object(Bucket='data-collection-059416028963-us-east-1-an',Key=key,Body=b'{"purpose":"authorized document capture permission check"}',ServerSideEncryption='AES256')
 s.get_object(Bucket='data-collection-059416028963-us-east-1-an',Key=key)['Body'].close()
 s.list_objects_v2(Bucket='data-collection-059416028963-us-east-1-an',Prefix='research-data/'+prefix,MaxKeys=1)
print('Required document state read/write/list permissions verified')
""")
 remote(T3,"""from pathlib import Path
import json,time,subprocess,os,signal
hold=Path('constellation/autostop/m7-deployment-hold.json');hold.write_text(json.dumps({'expires_at':time.time()+3600,'reason':'Final document capture cutover'}))
units=['optima-'+n+'.service'for n in NAMES]
for u in units:subprocess.run(['systemctl','stop',u.replace('.service','.timer')],check=True)
for p in Path('/proc').glob('[0-9]*'):
 try:
  a=(p/'cmdline').read_bytes().split(bytes([0]))
  if any(x.endswith(b'/s3_runtime.py')for x in a)and b'--unit'in a and a[a.index(b'--unit')+1].decode()in units:os.kill(int(p.name),signal.SIGINT)
 except(OSError,ValueError):pass
end=time.monotonic()+210
while any(subprocess.check_output(['systemctl','show',u,'-p','ActiveState','--value'],text=True).strip()in ('active','activating','deactivating')for u in units):
 if time.monotonic()>end:raise RuntimeError('Document capture still checkpointing; retain deployment hold')
 time.sleep(2)
print('Document captures checkpointed before handoff')
""".replace('NAMES',repr(NAMES)))
 s=session.client('s3');B='data-collection-059416028963-us-east-1-an';doc=json.loads(s.get_object(Bucket=B,Key='research-data/operations/s3-runtime/current.json')['Body'].read());entries={}
 for name,entry in doc['paths'].items():
  if name.startswith('nist-robotics.sqlite3'):
   dest='research-data/constellation-backfill/migration/capture-recheck/nist-'+entry['sha256']
   s.copy_object(Bucket=B,Key=dest,CopySource={'Bucket':B,'Key':entry['key']},ServerSideEncryption='AES256');entries[name]={**entry,'key':dest}
 key='research-data/constellation-backfill/migration/capture-recheck/nist-state.json';s.put_object(Bucket=B,Key=key,Body=json.dumps(entries).encode(),ServerSideEncryption='AES256')
 remote(M7,"""from pathlib import Path
import json,boto3,hashlib,os
s=boto3.client('s3',region_name='us-east-1');B='data-collection-059416028963-us-east-1-an';rows=json.loads(s.get_object(Bucket=B,Key='research-data/constellation-backfill/migration/capture-recheck/nist-state.json')['Body'].read())
for name,e in rows.items():
 raw=s.get_object(Bucket=B,Key=e['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==e['sha256'];p=Path(TARGET)/name;p.write_bytes(raw);os.chown(p,1000,1000)
print('Restored',len(rows),'verified NIST registry files')
""".replace('TARGET',repr(TARGET)))
 (ROOT/'config/m7-document-capture-active.json').write_text(json.dumps(NAMES))
 remote(T3,"""from pathlib import Path
import subprocess,json
for name in NAMES:
 unit='optima-'+name+'.service';target='optima-m7-capture-'+name+'.service';p=Path('/etc/systemd/system/'+unit+'.d');p.mkdir(exist_ok=True)
 (p/'zzzzzzzz-m7-capture.conf').write_text('[Service]\\nExecStart=\\nExecStart=/home/ec2-user/data-collection-processing/.venv-athena/bin/python -B -m constellation.m7_lifecycle dispatch --unit '+target+'\\nSlice=system.slice\\nMemoryHigh=128M\\nMemoryMax=256M\\nCPUQuota=50%\\nTimeoutStartSec=10min\\nReadWritePaths=/home/ec2-user/data-collection-processing/constellation/autostop\\n')
from monitoring_extra_jobs import extend
p=Path('config/collection-monitoring.json');d=json.loads(p.read_text());extend(d);p.write_text(json.dumps(d,indent=2)+'\\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
for name in NAMES:
 subprocess.run(['systemctl','restart','optima-'+name+'.timer'],check=True);subprocess.run(['systemctl','start','--no-block','optima-'+name+'.service'],check=True)
Path('constellation/autostop/m7-deployment-hold.json').unlink(missing_ok=True)
print('Final document dispatchers activated under shared lifecycle protection')
""".replace('NAMES',repr(NAMES)))

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','cutover']);args=p.parse_args();stage()if args.action=='stage'else cutover()
