import boto3,json
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('ssm',region_name='us-east-1')
for name in ('metadata-deployment','worker-check-command','replay-command'):
 f=p/(name+'.json')
 if not f.exists():continue
 r=json.load(open(f));x=s.get_command_invocation(CommandId=r['command_id'],InstanceId=r['instance']);(p/(name+'-result.json')).write_text(json.dumps(x,indent=2,default=str));print(name,x['Status'],x['StandardOutputContent'][-6000:],x['StandardErrorContent'][-2000:])
