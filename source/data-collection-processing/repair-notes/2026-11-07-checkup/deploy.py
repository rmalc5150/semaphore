import base64,json,hashlib
from pathlib import Path
import boto3
p=Path(__file__).parent;c=json.loads(Path('config/constellation-infrastructure.json').read_text());s=boto3.client('s3',region_name=c['region']);files={}
for name in ('personnel_archive.py','credential_source_apis.py','additional_source_apis.py'):
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key=c['prefix']+'/deployments/checkup-20261107/'+sha+'/'+name;s.put_object(Bucket=c['bucket'],Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
script='''import boto3,hashlib,json,os
from pathlib import Path
files=FILES;s=boto3.client('s3',region_name='us-east-1');count=0
for name,meta in files.items():
 raw=s.get_object(Bucket=BUCKET,Key=meta['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==meta['sha256'];compile(raw,name,'exec')
 for root in [Path('/opt/constellation/source'),*Path('/opt/constellation/legacy').glob('*')]:
  if not (root/'specialist_inputs.py').is_file():continue
  target=root/name;backup=Path('/opt/constellation/tmp/checkup1107-backup')/root.name/name;backup.parent.mkdir(parents=True,exist_ok=True)
  if target.exists() and not backup.exists():backup.write_bytes(target.read_bytes())
  temp=target.with_suffix('.repair.tmp');temp.write_bytes(raw);os.chmod(temp,0o644);temp.replace(target);count+=1
print(json.dumps({'updated_files':count,'modules':list(files)}))
'''.replace('FILES',repr(files)).replace('BUCKET',repr(c['bucket']))
encoded=base64.b64encode(script.encode()).decode();cmd="/opt/constellation/legacy-venv/bin/python -c \"import base64;exec(base64.b64decode('"+encoded+"'))\""
r=boto3.client('ssm',region_name=c['region']).send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=120)
(p/'deployment.json').write_text(json.dumps({'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id'],'files':files},indent=2))
for root in Path('constellation/daily-workspaces').glob('*'):
 if not (root/'specialist_inputs.py').is_file():continue
 for name in files:
  target=root/name;backup=p/'daily-backups'/root.name/name;backup.parent.mkdir(parents=True,exist_ok=True)
  if target.exists() and not backup.exists():backup.write_bytes(target.read_bytes())
  temp=target.with_suffix('.repair.tmp');temp.write_bytes(Path(name).read_bytes());temp.replace(target)
print(r['Command']['CommandId'])
