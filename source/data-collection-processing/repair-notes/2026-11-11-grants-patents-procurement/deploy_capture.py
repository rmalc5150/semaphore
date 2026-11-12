import boto3,json,hashlib,base64,time
from pathlib import Path
p=Path(__file__).parent;c=json.load(open('config/constellation-infrastructure.json'));s=boto3.client('s3',region_name=c['region']);files={}
for name in ('grants_review_capture.py','specialist_inputs.py','specialist_plan.py','nih_pagination.py','ted_enrichment.py','ted_packages.py','nist_robotics.py','specialist_public_apis.py'):
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key=c['prefix']+'/deployments/grants-review-20261111/'+sha+'/'+name;s.put_object(Bucket=c['bucket'],Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
sources=['nih_reporter','usa_spending','ted_notices','nist_robotics_methods'];name='optima-grants-reviewed-capture';unit='[Unit]\nDescription=Bounded grants/procurement daily capture; historical routes remain independent\nAfter=network-online.target\n[Service]\nType=oneshot\nUser=ec2-user\nWorkingDirectory=/opt/constellation/source\nExecStart=/opt/constellation/legacy-venv/bin/python -B grants_review_capture.py --sources '+' '.join(sources)+'\nSlice=constellation-workers.slice\nMemoryMax=402653184\nMemorySwapMax=0\nCPUQuota=20%\nTimeoutStartSec=300\nEnvironment=CONSTELLATION_ROLE=worker\nEnvironment=CONSTELLATION_SHARED_HTTP_LIMITS=1\n';timer='[Unit]\nDescription=Continue source-isolated grants/procurement capture\n[Timer]\nOnBootSec=300\nOnUnitInactiveSec=300\nPersistent=true\nUnit='+name+'.service\n[Install]\nWantedBy=timers.target\n';units={name+'.service':unit,name+'.timer':timer}
for n,b in units.items():(p/n).write_text(b)
script='''import boto3,json,hashlib,subprocess
from pathlib import Path
root=Path('/opt/constellation/source');s=boto3.client('s3',region_name='us-east-1')
for name,ref in FILES.items():
 raw=s.get_object(Bucket=BUCKET,Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];compile(raw,name,'exec');target=root/name;temp=target.with_suffix('.fda.tmp');temp.write_bytes(raw);temp.replace(target)
p=root/'config/specialist-inputs.json';data=json.loads(p.read_text())
for row in data['sources']:
 if row['source']in SOURCES:row['execution_lane']='grants_review'
 if row['source']=='uspto_assignment_histories':row['execution_lane']='controller_assignments_review'
p.write_text(json.dumps(data,indent=2)+chr(10))
for name,body in UNITS.items():Path('/etc/systemd/system/'+name).write_text(body)
subprocess.run(['systemctl','daemon-reload'],check=True);subprocess.run(['systemctl','enable','--now','optima-grants-reviewed-capture.timer'],check=True)
'''.replace('FILES',repr(files)).replace('BUCKET',repr(c['bucket'])).replace('SOURCES',repr(sources)).replace('UNITS',repr(units))
enc=base64.b64encode(script.encode()).decode();cmd='/opt/constellation/legacy-venv/bin/python -c "import base64;exec(base64.b64decode(\''+enc+'\'))"';a=boto3.client('ssm',region_name='us-east-1');r=a.send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=60);ref={'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id']};(p/'capture-deployment.json').write_text(json.dumps(ref))
for _ in range(50):
 try:o=a.get_command_invocation(CommandId=ref['command_id'],InstanceId=ref['instance'])
 except a.exceptions.InvocationDoesNotExist:time.sleep(1);continue
 if o['Status']not in ('Pending','InProgress','Delayed'):break
 time.sleep(1)
(p/'capture-deployment-result.json').write_text(json.dumps(o,indent=2,default=str));print(o['Status'],o['StandardErrorContent']);assert o['Status']=='Success'
