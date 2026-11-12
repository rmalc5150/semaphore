"""Atomically update compatible collector modules without restarting worker pools."""
import base64,hashlib,json,shlex
from pathlib import Path
from constellation.control import Control
ROOT=Path(__file__).resolve().parents[2]
FILES=('public_source_capture.py','specialist_inputs.py','specialist_plan.py','additional_source_apis.py','additional_source_plan.py','epo_ops.py','credential_source_apis.py','copernicus_capture.py')
CONFIG_FILES=('constellation-public-sources.json','constellation-specialist-historical.json','specialist-inputs.json')

def main():
    c=Control();objects={}
    for name in FILES:
        body=(ROOT/name).read_bytes();digest=hashlib.sha256(body).hexdigest();key=c.config['prefix']+'/deployments/source-fix-'+digest+'/'+name
        c.s3.put_object(Bucket=c.config['bucket'],Key=key,Body=body,ServerSideEncryption='AES256');objects[name]={'key':key,'sha256':digest}
        for workspace in (ROOT/'constellation/daily-workspaces').iterdir():
            target=workspace/name;temporary=target.with_suffix('.updated');temporary.write_text(body.decode().replace(str(ROOT),str(workspace)));temporary.replace(target)
    for name in CONFIG_FILES:
        body=(ROOT/'config'/name).read_bytes();digest=hashlib.sha256(body).hexdigest();key=c.config['prefix']+'/deployments/source-fix-'+digest+'/config/'+name
        object_name='config/'+name;objects[object_name]={'key':key,'sha256':digest}
        c.s3.put_object(Bucket=c.config['bucket'],Key=key,Body=body,ServerSideEncryption='AES256')
        for workspace in (ROOT/'constellation/daily-workspaces').iterdir():
            target=workspace/'config'/name;temporary=target.with_suffix('.updated');temporary.write_text(body.decode().replace(str(ROOT),str(workspace)));temporary.replace(target)
    code='''from pathlib import Path
import boto3,os,hashlib
s3=boto3.client('s3',region_name='us-east-1');base=Path('/opt/constellation')
for name,object in OBJECTS.items():
 response=s3.get_object(Bucket=BUCKET,Key=object['key']);body=response['Body'].read();response['Body'].close()
 if hashlib.sha256(body).hexdigest()!=object['sha256']:raise RuntimeError('Collector code checksum mismatch')
 for root in [base/'source',*[p for p in (base/'legacy').iterdir() if p.is_dir()]]:
  target=root/name;target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_suffix('.updated');temporary.write_text(body.decode().replace('/home/ec2-user/data-collection-processing',str(root)));os.chown(temporary,1000,1000);temporary.replace(target)
print('Collector modules updated atomically after SHA-256 verification; worker pools retained.')
'''.replace('OBJECTS',repr(objects)).replace('BUCKET',repr(c.config['bucket']))
    command='/opt/constellation/.venv/bin/python -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(base64.b64encode(code.encode()).decode())+'))')
    worker=c.session.client('ssm').send_command(InstanceIds=[c.config['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[command]},TimeoutSeconds=120)
    controller_code='''from pathlib import Path
import boto3,os,hashlib
s3=boto3.client('s3',region_name='us-east-1');base=Path('/home/ec2-user/data-collection-processing')
for name,object in OBJECTS.items():
 response=s3.get_object(Bucket=BUCKET,Key=object['key']);body=response['Body'].read();response['Body'].close()
 if hashlib.sha256(body).hexdigest()!=object['sha256']:raise RuntimeError('Collector code checksum mismatch')
 for root in [base,*[p for p in (base/'constellation/daily-workspaces').iterdir() if p.is_dir()]]:
  target=root/name;target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_suffix('.updated');temporary.write_text(body.decode().replace('/home/ec2-user/data-collection-processing',str(root)));os.chown(temporary,1000,1000);temporary.replace(target)
print('Controller public collectors and isolated daily workspaces updated after SHA-256 verification.')
'''.replace('OBJECTS',repr(objects)).replace('BUCKET',repr(c.config['bucket']))
    controller_command='/home/ec2-user/data-collection-processing/.venv-athena/bin/python -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(base64.b64encode(controller_code.encode()).decode())+'))')
    controller=c.session.client('ssm').send_command(InstanceIds=[c.config['controller_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[controller_command]},TimeoutSeconds=120)
    receipt={'worker_command_id':worker['Command']['CommandId'],'controller_command_id':controller['Command']['CommandId'],'modules':objects,'workers_restarted':False};(ROOT/'constellation/expansion/public-code-refresh.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':main()
