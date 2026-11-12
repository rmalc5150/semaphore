import json,base64
from pathlib import Path
import boto3
p=Path(__file__).parent;c=json.loads(Path('config/constellation-infrastructure.json').read_text())
script='''import boto3,json,uuid,hashlib
from datetime import datetime,timezone
session=boto3.Session(region_name='us-east-1');arn=session.client('sts').get_caller_identity()['Arn']
assert ':assumed-role/constellation-backfill-worker/' in arn, 'Unexpected worker role'
s=session.client('s3');bucket=BUCKET;run=uuid.uuid4().hex;results=[]
body=json.dumps({'purpose':'owner-approved BLS permission verification','at':datetime.now(timezone.utc).isoformat(),'run_id':run}).encode()
for prefix in ('joins-cache','observed','versions'):
 key='research-data/operations/bls-labor/'+prefix+'/permission-verification/'+run+'.json'
 s.put_object(Bucket=bucket,Key=key,Body=body,ContentType='application/json',ServerSideEncryption='AES256',IfNoneMatch='*')
 response=s.get_object(Bucket=bucket,Key=key)
 try:read=response['Body'].read()
 finally:response['Body'].close()
 assert read==body
 results.append({'prefix':prefix,'put':'verified','get':'verified','evidence_key':key,'sha256':hashlib.sha256(read).hexdigest()})
print(json.dumps({'role':arn,'results':results,'production_records_modified':False}))
'''.replace('BUCKET',repr(c['bucket']))
encoded=base64.b64encode(script.encode()).decode();command="/opt/constellation/.venv/bin/python -c \"import base64;exec(base64.b64decode('"+encoded+"'))\""
r=boto3.client('ssm',region_name=c['region']).send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[command]},TimeoutSeconds=120)
(p/'bls-permission-verification-command.json').write_text(json.dumps({'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id']},indent=2));print(r['Command']['CommandId'])
