import json,hashlib,base64,boto3
from pathlib import Path
p=Path(__file__).parent;c=json.load(open('config/constellation-infrastructure.json'));s=boto3.client('s3',region_name=c['region']);files={}
for target,path in [('worker_capture.py',p/'worker_capture.py'),('disclosure_content_backfill.py',Path('disclosure_content_backfill.py')),('config/s11-content-backfill.json',Path('config/s11-content-backfill.json'))]:
 raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest();key=c['prefix']+'/deployments/disclosure-resume-20261109/'+sha+'/'+target;s.put_object(Bucket=c['bucket'],Key=key,Body=raw,ServerSideEncryption='AES256');files[target]={'key':key,'sha256':sha}
code='''import boto3,hashlib,os,json,subprocess
from pathlib import Path
files=FILES;s=boto3.client('s3',region_name='us-east-1');root=Path('/opt/constellation/legacy/optima-s11-content-backfill.service');assert(root/'disclosure_collection.py').is_file()
for name,meta in files.items():
 raw=s.get_object(Bucket=BUCKET,Key=meta['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==meta['sha256']
 if name.endswith('.py'):compile(raw,name,'exec')
 target=root/name;backup=Path('/opt/constellation/tmp/disclosure-resume1109-backup')/name;backup.parent.mkdir(parents=True,exist_ok=True)
 if target.exists() and not backup.exists():backup.write_bytes(target.read_bytes())
 temp=target.with_suffix('.repair.tmp');temp.write_bytes(raw);os.chmod(temp,0o644);temp.replace(target)
for mode,seconds in [('daily',120),('historical',300)]:
 unit='optima-disclosure-'+mode
 service=f'[Unit]\\nDescription=Bounded disclosure {mode} capture and candidate extraction\\nAfter=network-online.target\\n[Service]\\nType=oneshot\\nUser=ec2-user\\nWorkingDirectory={root}\\nExecStart=/usr/bin/flock --nonblock --conflict-exit-code 75 /opt/constellation/tmp/disclosure-capture.lock /opt/constellation/legacy-venv/bin/python -B {root}/worker_capture.py --mode {mode}\\nSlice=constellation-workers.slice\\nMemoryHigh=402653184\\nMemoryMax=536870912\\nMemorySwapMax=0\\nCPUQuota=25%\\nTimeoutStartSec=900\\nTimeoutStopSec=90\\nKillSignal=SIGINT\\nSuccessExitStatus=0 2 75\\nEnvironment=CONSTELLATION_ROLE=worker\\nEnvironment=CONSTELLATION_SHARED_HTTP_LIMITS=1\\nEnvironment=PYTHONDONTWRITEBYTECODE=1\\nEnvironment=MALLOC_ARENA_MAX=2\\nNice=15\\n'
 timer=f'[Unit]\\nDescription=Resume bounded disclosure {mode} capture\\n[Timer]\\nOnBootSec=90\\nOnUnitInactiveSec={seconds}\\nPersistent=true\\n[Install]\\nWantedBy=timers.target\\n'
 Path('/etc/systemd/system/'+unit+'.service').write_text(service.replace(chr(92)+"n",chr(10)));Path('/etc/systemd/system/'+unit+'.timer').write_text(timer.replace(chr(92)+"n",chr(10)))
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','optima-disclosure-daily.timer','optima-disclosure-historical.timer'],check=True)
subprocess.run(['systemctl','start','--no-block','optima-disclosure-daily.service'],check=True)
print(json.dumps({'deployed_files':list(files),'daily_and_historical_timers':'enabled','root':str(root)}))
'''.replace('FILES',repr(files)).replace('BUCKET',repr(c['bucket']))
enc=base64.b64encode(code.encode()).decode();cmd="/opt/constellation/legacy-venv/bin/python -c \"import base64;exec(base64.b64decode('"+enc+"'))\""
r=boto3.client('ssm',region_name=c['region']).send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=120);(p/'deployment.json').write_text(json.dumps({'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id'],'files':files},indent=2));print(r['Command']['CommandId'])
