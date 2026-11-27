import json,boto3,time,base64,sys
from pathlib import Path
p=Path(__file__).parent;name=sys.argv[1];script=Path(sys.argv[2]).read_text();enc=base64.b64encode(script.encode()).decode();cmd="AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_DEFAULT_REGION=us-east-1 AWS_REGION=us-east-1 /opt/constellation/legacy-venv/bin/python -c \"import base64;exec(base64.b64decode('"+enc+"'))\"";a=boto3.client('ssm',region_name='us-east-1');r=a.send_command(InstanceIds=['i-06241bd1c4e91c2fc'],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd],'executionTimeout':['600']},TimeoutSeconds=630);ref={'command_id':r['Command']['CommandId'],'instance':'i-06241bd1c4e91c2fc'};(p/(name+'-command.json')).write_text(json.dumps(ref));print(ref,flush=True)
for _ in range(310):
 try:o=a.get_command_invocation(CommandId=ref['command_id'],InstanceId=ref['instance'])
 except a.exceptions.InvocationDoesNotExist:time.sleep(2);continue
 if o['Status']not in ('Pending','InProgress','Delayed'):break
 time.sleep(2)
(p/(name+'-result.json')).write_text(json.dumps(o,indent=2,default=str));print(o['Status'],o['StandardOutputContent'],o['StandardErrorContent']);assert o['Status']=='Success'
