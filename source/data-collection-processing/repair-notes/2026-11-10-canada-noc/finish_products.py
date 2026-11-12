import base64,boto3,json
from pathlib import Path
p=Path(__file__).parent
script='''import boto3,json,subprocess
s=boto3.client('s3',region_name='us-east-1')
for step in range(22):
 subprocess.run(['systemctl','start','optima-canada-noc-products.service'],check=True)
 r=json.loads(s.get_object(Bucket='data-collection-059416028963-us-east-1-an',Key='research-data/constellation-backfill/legacy-operation-receipts/canada-noc-products/2026-11-10/progress.json')['Body'].read());print(json.dumps({'step':step,'captured_rows':r['captured_rows'],'status':r['status']}),flush=True)
 if r['status']=='complete':break
else:raise RuntimeError('bounded_product_replay_not_finished')
'''
enc=base64.b64encode(script.encode()).decode();cmd="systemd-run --unit=optima-canada-noc-product-repair-20261110-v2 --property=RuntimeMaxSec=900 --property=MemoryMax=134217728 --property=CPUQuota=5% --property=Slice=constellation-workers.slice /opt/constellation/legacy-venv/bin/python -c \"import base64;exec(base64.b64decode('"+enc+"'))\""
r=boto3.client('ssm',region_name='us-east-1').send_command(InstanceIds=['i-06241bd1c4e91c2fc'],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=60);(p/'finish-products-command.json').write_text(json.dumps({'command_id':r['Command']['CommandId'],'instance':'i-06241bd1c4e91c2fc'},indent=2));print(r['Command']['CommandId'])
