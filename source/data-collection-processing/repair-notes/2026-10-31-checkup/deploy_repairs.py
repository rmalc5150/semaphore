import base64,json,hashlib
from pathlib import Path
import boto3
p=Path(__file__).parent;c=json.loads(Path('config/constellation-infrastructure.json').read_text());s=boto3.client('s3',region_name=c['region']);raw=Path('additional_source_apis.py').read_bytes();sha=hashlib.sha256(raw).hexdigest();key=c['prefix']+'/deployments/checkup-20261031/'+sha+'/additional_source_apis.py';s.put_object(Bucket=c['bucket'],Key=key,Body=raw,ServerSideEncryption='AES256')
script='''import boto3,hashlib,json,os
from pathlib import Path
raw=boto3.client('s3',region_name='us-east-1').get_object(Bucket=BUCKET,Key=KEY)['Body'].read();assert hashlib.sha256(raw).hexdigest()==SHA
roots=[Path('/opt/constellation/source'),*Path('/opt/constellation/legacy').glob('*')];updated=[]
for root in roots:
 target=root/'additional_source_apis.py'
 if not target.is_file():continue
 compile(raw,str(target),'exec');backup=Path('/opt/constellation/tmp/checkup31-backup')/root.name/'additional_source_apis.py';backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():backup.write_bytes(target.read_bytes())
 temp=target.with_suffix('.checkup31.tmp');temp.write_bytes(raw);os.chmod(temp,target.stat().st_mode);temp.replace(target);updated.append(str(target))
print(json.dumps({'updated_files':len(updated),'sha256':SHA}))
'''.replace('BUCKET',repr(c['bucket'])).replace('KEY',repr(key)).replace('SHA',repr(sha))
encoded=base64.b64encode(script.encode()).decode();cmd="/opt/constellation/legacy-venv/bin/python -c \"import base64;exec(base64.b64decode('"+encoded+"'))\"";r=boto3.client('ssm',region_name=c['region']).send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=120)
(p/'deployment.json').write_text(json.dumps({'command_id':r['Command']['CommandId'],'sha256':sha,'instance':c['worker_instance_id']},indent=2))
n=0
for target in Path('constellation/daily-workspaces').glob('*/additional_source_apis.py'):
 temp=target.with_suffix('.checkup31.tmp');temp.write_bytes(raw);temp.replace(target);n+=1
print('Deployment requested',r['Command']['CommandId'],'daily copies',n)
