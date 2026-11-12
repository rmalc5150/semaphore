import boto3,json,hashlib,base64
from pathlib import Path
p=Path(__file__).parent;c=json.load(open('config/constellation-infrastructure.json'));s=boto3.client('s3',region_name=c['region']);files={}
for name in ['drugsfda_inventory_worker.py','specialist_plan.py','specialist_public_apis.py','specialist_inputs.py','config/drugsfda-inventory-universe.json']:
 if name.endswith('.json'):
  index=json.loads(s.get_object(Bucket=c['bucket'],Key='research-data/operations/s3-runtime/current.json')['Body'].read());ref=index['paths']['config/company-universe.v0.5.json'];raw=s.get_object(Bucket=c['bucket'],Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256']
 else:raw=Path(name).read_bytes()
 sha=hashlib.sha256(raw).hexdigest();key=c['prefix']+'/deployments/drugsfda-inventory-20261110/'+sha+'/'+name;s.put_object(Bucket=c['bucket'],Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
script="""import boto3,hashlib,subprocess
from pathlib import Path
root=Path('/opt/constellation/source');s=boto3.client('s3',region_name='us-east-1')
for name,ref in FILES.items():
 raw=s.get_object(Bucket=BUCKET,Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];target=root/name;
 if name.endswith('.py'):compile(raw,name,'exec')
 else:__import__('json').loads(raw)
 backup=Path('/opt/constellation/tmp/drugsfda-inventory-backup')/name;backup.parent.mkdir(parents=True,exist_ok=True)
 if target.exists()and not backup.exists():backup.write_bytes(target.read_bytes())
 temp=target.with_suffix('.repair.tmp');temp.write_bytes(raw);temp.chmod(0o644);temp.replace(target)
Path('/etc/systemd/system/optima-drugsfda-inventory.service').write_text(UNIT)
Path('/etc/systemd/system/optima-drugsfda-inventory.timer').write_text(TIMER)
subprocess.run(['systemctl','daemon-reload'],check=True);subprocess.run(['systemctl','enable','--now','optima-drugsfda-inventory.timer'],check=True);subprocess.run(['systemctl','start','--no-block','optima-drugsfda-inventory.service'],check=True)
"""
unit='[Unit]\nDescription=Bounded all-provider DrugsFDA application inventory\nAfter=network-online.target\n[Service]\nType=oneshot\nUser=ec2-user\nWorkingDirectory=/opt/constellation/source\nExecStart=/opt/constellation/legacy-venv/bin/python -B drugsfda_inventory_worker.py\nSlice=constellation-workers.slice\nMemoryMax=402653184\nMemorySwapMax=0\nCPUQuota=20%\nTimeoutStartSec=300\nEnvironment=CONSTELLATION_SHARED_HTTP_LIMITS=1\nEnvironment=CONSTELLATION_ROLE=worker\n'
timer='[Unit]\nDescription=Continue bounded DrugsFDA inventory\n[Timer]\nOnBootSec=120\nOnUnitInactiveSec=120\nUnit=optima-drugsfda-inventory.service\n[Install]\nWantedBy=timers.target\n'
(p/'optima-drugsfda-inventory.service').write_text(unit);(p/'optima-drugsfda-inventory.timer').write_text(timer)
script=script.replace('FILES',repr(files)).replace('BUCKET',repr(c['bucket'])).replace('UNIT',repr(unit)).replace('TIMER',repr(timer));enc=base64.b64encode(script.encode()).decode();cmd='/opt/constellation/legacy-venv/bin/python -c "import base64;exec(base64.b64decode(\''+enc+'\'))"'
r=boto3.client('ssm',region_name=c['region']).send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=60);(p/'inventory-deployment.json').write_text(json.dumps({'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id']},indent=2));print(r['Command']['CommandId'])
