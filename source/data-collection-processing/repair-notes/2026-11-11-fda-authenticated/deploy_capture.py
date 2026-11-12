import boto3,json,hashlib,base64,time
from pathlib import Path
p=Path(__file__).parent;c=json.load(open('config/constellation-infrastructure.json'));s=boto3.client('s3',region_name=c['region']);files={}
for name in ('fda_review_capture.py','specialist_authenticated.py'):
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key=c['prefix']+'/deployments/fda-review-20261111/'+sha+'/'+name;s.put_object(Bucket=c['bucket'],Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
sources=['fda_dd_compliance_actions','fda_dd_import_refusals','fda_dd_inspections_citations','fda_ires_recalls'];name='optima-fda-reviewed-capture';unit='[Unit]\nDescription=Bounded FDA daily capture; historical routes remain independent\nAfter=network-online.target\n[Service]\nType=oneshot\nUser=ec2-user\nWorkingDirectory=/opt/constellation/source\nExecStart=/opt/constellation/legacy-venv/bin/python -B fda_review_capture.py --sources '+' '.join(sources)+'\nSlice=constellation-workers.slice\nMemoryMax=402653184\nMemorySwapMax=0\nCPUQuota=20%\nTimeoutStartSec=300\nEnvironment=CONSTELLATION_ROLE=worker\nEnvironment=CONSTELLATION_SHARED_HTTP_LIMITS=1\n';timer='[Unit]\nDescription=Continue source-isolated FDA capture\n[Timer]\nOnBootSec=120\nOnUnitInactiveSec=120\nPersistent=true\nUnit='+name+'.service\n[Install]\nWantedBy=timers.target\n';units={name+'.service':unit,name+'.timer':timer}
for n,b in units.items():(p/n).write_text(b)
script='''import boto3,json,hashlib,subprocess
from pathlib import Path
root=Path('/opt/constellation/source');s=boto3.client('s3',region_name='us-east-1')
for name,ref in FILES.items():
 raw=s.get_object(Bucket=BUCKET,Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];compile(raw,name,'exec');target=root/name;temp=target.with_suffix('.fda.tmp');temp.write_bytes(raw);temp.replace(target)
p=root/'config/specialist-inputs.json';data=json.loads(p.read_text())
for row in data['sources']:
 if row['source']in SOURCES:row['execution_lane']='fda_review'
p.write_text(json.dumps(data,indent=2)+chr(10))
for name,body in UNITS.items():Path('/etc/systemd/system/'+name).write_text(body)
subprocess.run(['systemctl','daemon-reload'],check=True);subprocess.run(['systemctl','enable','--now','optima-fda-reviewed-capture.timer'],check=True)
'''.replace('FILES',repr(files)).replace('BUCKET',repr(c['bucket'])).replace('SOURCES',repr(sources)).replace('UNITS',repr(units))
enc=base64.b64encode(script.encode()).decode();cmd='/opt/constellation/legacy-venv/bin/python -c "import base64;exec(base64.b64decode(\''+enc+'\'))"';a=boto3.client('ssm',region_name='us-east-1');r=a.send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=60);ref={'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id']};(p/'capture-deployment.json').write_text(json.dumps(ref))
for _ in range(50):
 try:o=a.get_command_invocation(CommandId=ref['command_id'],InstanceId=ref['instance'])
 except a.exceptions.InvocationDoesNotExist:time.sleep(1);continue
 if o['Status']not in ('Pending','InProgress','Delayed'):break
 time.sleep(1)
(p/'capture-deployment-result.json').write_text(json.dumps(o,indent=2,default=str));print(o['Status'],o['StandardErrorContent']);assert o['Status']=='Success'
probe="systemd-run --unit=optima-fda-review-probes-v3 --wait --property=User=ec2-user --property=WorkingDirectory=/opt/constellation/source --property=Slice=constellation-workers.slice --property=MemoryMax=402653184 --property=CPUQuota=20% --property=RuntimeMaxSec=360 --setenv=CONSTELLATION_ROLE=worker --setenv=CONSTELLATION_SHARED_HTTP_LIMITS=1 /opt/constellation/legacy-venv/bin/python -B fda_review_capture.py --probe --sources "+' '.join(sources)
r=a.send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[probe]},TimeoutSeconds=390);(p/'fresh-probes-command.json').write_text(json.dumps({'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id']}));print('Fresh probes',r['Command']['CommandId'])
