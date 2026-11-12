import boto3,json,hashlib,base64,time
from pathlib import Path
p=Path(__file__).parent;c=json.load(open('config/constellation-infrastructure.json'));s=boto3.client('s3',region_name=c['region']);files={}
for name in ['crossref_resumed_capture.py','conference_collection.py','config/crossref-resumed-universe.json','historical_policy.py','config/historical-collection.json']:
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key=c['prefix']+'/deployments/crossref-resumed-20261110/'+sha+'/'+name;s.put_object(Bucket=c['bucket'],Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
unit='''[Unit]
Description=Bounded Crossref daily and historical continuation
After=network-online.target
[Service]
Type=oneshot
User=ec2-user
WorkingDirectory=/opt/constellation/source
ExecStart=/opt/constellation/legacy-venv/bin/python -B crossref_resumed_capture.py
Slice=constellation-workers.slice
MemoryMax=402653184
MemorySwapMax=0
CPUQuota=20%
TimeoutStartSec=300
Environment=CONSTELLATION_SHARED_HTTP_LIMITS=1
Environment=CONSTELLATION_ROLE=worker
'''
timer='''[Unit]
Description=Bounded Crossref daily and historical continuation
[Timer]
OnBootSec=180
OnUnitInactiveSec=120
Persistent=true
Unit=optima-crossref-resumed.service
[Install]
WantedBy=timers.target
'''
(p/'optima-crossref-resumed.service').write_text(unit);(p/'optima-crossref-resumed.timer').write_text(timer)
script='''import boto3,hashlib,subprocess
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');root=Path('/opt/constellation/source')
for name,ref in FILES.items():
 raw=s.get_object(Bucket=BUCKET,Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];__import__('json').loads(raw) if name.endswith('.json') else compile(raw,name,'exec');target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
import json
for ref in SEEDS:
 target='research-data/constellation-backfill/conferences-resumed/progress/'+ref['key'].rsplit('/',1)[1]
 try:s.head_object(Bucket=BUCKET,Key=target)
 except s.exceptions.ClientError as error:
  if error.response['Error']['Code'] not in ('404','NoSuchKey','NotFound'):raise
  s.put_object(Bucket=BUCKET,Key=target,Body=json.dumps(ref['state']).encode(),ContentType='application/json',ServerSideEncryption='AES256',IfNoneMatch='*')
Path('/etc/systemd/system/optima-crossref-resumed.service').write_text(UNIT)
Path('/etc/systemd/system/optima-crossref-resumed.timer').write_text(TIMER)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','optima-crossref-resumed.timer'],check=True)
subprocess.run(['systemctl','start','--no-block','optima-crossref-resumed.service'],check=True)
'''.replace('SEEDS',repr(json.load(open(p/'progress-before.json')))).replace('FILES',repr(files)).replace('BUCKET',repr(c['bucket'])).replace('UNIT',repr(unit)).replace('TIMER',repr(timer))
enc=base64.b64encode(script.encode()).decode();cmd='/opt/constellation/legacy-venv/bin/python -c "import base64;exec(base64.b64decode(\''+enc+'\'))"';a=boto3.client('ssm',region_name=c['region']);r=a.send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=60);ref={'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id']};(p/'capture-deployment.json').write_text(json.dumps(ref,indent=2))
for _ in range(25):
 try:out=a.get_command_invocation(CommandId=ref['command_id'],InstanceId=ref['instance'])
 except a.exceptions.InvocationDoesNotExist:time.sleep(1);continue
 if out['Status'] not in ('Pending','InProgress','Delayed'):break
 time.sleep(1)
(p/'capture-deployment-result.json').write_text(json.dumps(out,indent=2,default=str));print(out['Status'],out.get('StandardErrorContent',''));assert out['Status']=='Success'
