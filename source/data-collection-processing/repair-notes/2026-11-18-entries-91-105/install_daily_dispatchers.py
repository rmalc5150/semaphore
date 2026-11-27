from ops import *
import hashlib
from constellation.m7_capture_plan import PUBLIC_FILE_JOBS
refs={}
for name in ['constellation/m7_capture_plan.py','m7_capture_worker.py']:
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key=BASE+'deployment/'+sha+'/'+name;session.client('s3').put_object(Bucket=B,Key=key,Body=raw,ServerSideEncryption='AES256');refs[name]=(key,sha)
common=r'''import json,boto3,hashlib,os,subprocess,re
from pathlib import Path
names=NAMES;refs=REFS;s=boto3.client('s3',region_name='us-east-1');bucket=BUCKET
for root in roots:
 for name,(key,sha)in refs.items():
  raw=s.get_object(Bucket=bucket,Key=key)['Body'].read();assert hashlib.sha256(raw).hexdigest()==sha;compile(raw,name,'exec');p=root/name;p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.daily-stage');tmp.write_bytes(raw);os.chown(tmp,1000,1000);tmp.replace(p)
def retire(path):
 cfg=json.loads(path.read_text());changed=[]
 for row in cfg['routes']:
  if row['unit'].startswith('constellation-public-daily-')and any(source in row['unit']for source in names.values()):
   row.update(execution_enabled=False,activation_staged=False,remaining_requirements=['Replaced by lifecycle daily capture dispatcher, independent of historical enable/deadline']);changed.append(row['unit'])
 tmp=path.with_name(path.name+'.daily-stage');tmp.write_text(json.dumps(cfg,indent=2)+'\n');os.chown(tmp,1000,1000);tmp.replace(path);return changed
'''.replace('NAMES',repr(PUBLIC_FILE_JOBS)).replace('REFS',repr(refs)).replace('BUCKET',repr(B))
code="from pathlib import Path\nroots=[Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/source')]\n"+common+r'''
root=roots[0];template=Path('/etc/systemd/system/optima-m7-capture-eodhd-profiles.service').read_text()
for name in names:
 unit='optima-m7-capture-'+name+'.service';text=template.replace('eodhd-profiles',name);text=re.sub(r'(?m)^WorkingDirectory=.*$', 'WorkingDirectory='+str(root),text)
 Path('/etc/systemd/system/'+unit).write_text(text)
 tmp=Path('/opt/constellation/tmp/publication-staging')/unit;tmp.mkdir(parents=True,exist_ok=True);os.chown(tmp,1000,1000)
retire(Path('/opt/constellation/config/constellation-legacy-routes.json'))
for root in roots:
 p=root/'config/constellation-legacy-routes.json'
 if p.exists():retire(p)
subprocess.run(['systemctl','daemon-reload'],check=True);subprocess.run(['systemd-analyze','verify',*['optima-m7-capture-'+name+'.service'for name in names]],check=True)
print(json.dumps({'worker_daily_units':['optima-m7-capture-'+name+'.service'for name in names]}))
'''
print(remote(M7,code)['out'])
code="from pathlib import Path\nroots=[Path.cwd()]\n"+common+r'''
root=Path.cwd();retired=retire(root/'config/constellation-legacy-routes.json');system=Path('/etc/systemd/system')
for name in names:
 unit='optima-'+name+'.service';target='optima-m7-capture-'+name+'.service'
 text='[Unit]\nDescription=Dispatch large daily public capture to m7: '+name+'\nAfter=network-online.target\n[Service]\nType=oneshot\nUser=ec2-user\nWorkingDirectory='+str(root)+'\nExecStart='+str(root/'.venv-athena/bin/python')+' -B -m constellation.m7_lifecycle dispatch --unit '+target+'\nMemoryMax=256M\nCPUQuota=50%\nTimeoutStartSec=10min\nEnvironment=AWS_CONFIG_FILE=/dev/null\nEnvironment=AWS_SHARED_CREDENTIALS_FILE=/dev/null\nEnvironment=AWS_DEFAULT_REGION=us-east-1\nEnvironment=CONSTELLATION_ROLE=controller\n'
 (system/unit).write_text(text);(system/('optima-'+name+'.timer')).write_text('[Unit]\nDescription=Schedule large daily public capture on m7\n[Timer]\nOnCalendar=*-*-* 00,06,12,18:35:00 UTC\nPersistent=true\nUnit='+unit+'\n[Install]\nWantedBy=timers.target\n')
from constellation.control import Control
c=Control();backup=[]
with c.db()as cursor:
 for unit in retired:
  key='legacy:'+unit;cursor.execute("SELECT * FROM backfill_jobs WHERE source_key=%s AND status IN ('pending','retryable_failed') FOR UPDATE",(key,));backup+=cursor.fetchall();cursor.execute("UPDATE backfill_jobs SET status='blocked',lease_until=0,result_json=%s,updated_at=UNIX_TIMESTAMP() WHERE source_key=%s AND status IN ('pending','retryable_failed')",(json.dumps({'reason':'deliberately_replaced_by_daily_lifecycle_dispatcher','retired_duplicate':True}),key))
s.put_object(Bucket=bucket,Key=BASE+'retired-provisional-daily-route-jobs.json',Body=json.dumps(backup,default=str).encode(),ServerSideEncryption='AES256')
subprocess.run(['systemctl','daemon-reload'],check=True);subprocess.run(['systemd-analyze','verify',*['optima-'+name+'.service'for name in names],*['optima-'+name+'.timer'for name in names]],check=True)
print(json.dumps({'controller_dispatchers':['optima-'+name+'.service'for name in names],'timers_staged_not_started':True,'retired_duplicate_routes':retired}))
'''.replace('BASE',repr(BASE))
r=remote(T3,code);print(r['out']);(P/'daily-dispatchers-installed.json').write_text(r['out'])
