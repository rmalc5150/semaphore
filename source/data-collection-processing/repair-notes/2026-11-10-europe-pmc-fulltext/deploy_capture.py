import boto3,json,hashlib,base64,time
from pathlib import Path
p=Path(__file__).parent;c=json.load(open('config/constellation-infrastructure.json'));s=boto3.client('s3',region_name=c['region']);files={}
for name in ['epmc_fulltext_capture.py','specialist_inputs.py','metadata_engine/epmc_fulltext.py']:
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key=c['prefix']+'/deployments/epmc-fulltext-capture-20261110/'+sha+'/'+name;s.put_object(Bucket=c['bucket'],Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
units={}
for mode in ('discover','capture'):
 name='optima-epmc-fulltext-'+mode
 unit='[Unit]\nDescription=Bounded Europe PMC full-text '+mode+'\nAfter=network-online.target\n[Service]\nType=oneshot\nUser=ec2-user\nWorkingDirectory=/opt/constellation/source\nExecStart=/opt/constellation/legacy-venv/bin/python -B epmc_fulltext_capture.py --mode '+mode+'\nSlice=constellation-workers.slice\nMemoryMax=402653184\nMemorySwapMax=0\nCPUQuota=20%\nTimeoutStartSec=300\nEnvironment=CONSTELLATION_SHARED_HTTP_LIMITS=1\nEnvironment=CONSTELLATION_ROLE=worker\n'
 timer='[Unit]\nDescription=Continue Europe PMC full-text '+mode+'\n[Timer]\nOnBootSec=120\nOnUnitInactiveSec=120\nPersistent=true\nUnit='+name+'.service\n[Install]\nWantedBy=timers.target\n'
 units[name+'.service']=unit;units[name+'.timer']=timer
 (p/(name+'.service')).write_text(unit);(p/(name+'.timer')).write_text(timer)
script='''import boto3,hashlib,subprocess
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');root=Path('/opt/constellation/source')
for name,ref in FILES.items():
 raw=s.get_object(Bucket=BUCKET,Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];compile(raw,name,'exec');target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
import json
cfg=root/'config/specialist-inputs.json';plan=json.loads(cfg.read_text())
for source in plan['sources']:
 if source['source']=='europe_pmc':source['execution_lane']='epmc_discovery'
cfg.write_text(json.dumps(plan,indent=2)+chr(10))
for name,body in UNITS.items():Path('/etc/systemd/system/'+name).write_text(body)
subprocess.run(['systemctl','daemon-reload'],check=True)
for mode in ('discover','capture'):
 name='optima-epmc-fulltext-'+mode
 subprocess.run(['systemctl','enable','--now',name+'.timer'],check=True)
 subprocess.run(['systemctl','start','--no-block',name+'.service'],check=True)
'''.replace('FILES',repr(files)).replace('BUCKET',repr(c['bucket'])).replace('UNITS',repr(units))
enc=base64.b64encode(script.encode()).decode();cmd='/opt/constellation/legacy-venv/bin/python -c "import base64;exec(base64.b64decode(\''+enc+'\'))"';a=boto3.client('ssm',region_name=c['region']);r=a.send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=60);ref={'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id']};(p/'capture-deployment.json').write_text(json.dumps(ref,indent=2))
for _ in range(25):
 try:out=a.get_command_invocation(CommandId=ref['command_id'],InstanceId=ref['instance'])
 except a.exceptions.InvocationDoesNotExist:time.sleep(1);continue
 if out['Status'] not in ('Pending','InProgress','Delayed'):break
 time.sleep(1)
(p/'capture-deployment-result.json').write_text(json.dumps(out,indent=2,default=str));print(out['Status'],out.get('StandardErrorContent',''));assert out['Status']=='Success'
