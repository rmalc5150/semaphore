import json,boto3
from pathlib import Path
from collection_storage import StorageSettings
p=Path(__file__).parent;store=StorageSettings.load('config/collection-storage.s3.json').store();r=store.get('constellation-backfill/legacy-operation-receipts/canada-noc-products/2026-11-10/progress.json');(p/'products-progress.json').write_bytes(r.body);print(r.body.decode())
s=boto3.client('ssm',region_name='us-east-1');cmd="systemctl show optima-canada-noc-product-repair-20261110-v2.service optima-canada-noc-products.service -p ActiveState -p Result -p ExecMainStatus; journalctl -u optima-canada-noc-product-repair-20261110-v2.service -n 6 --no-pager";r=s.send_command(InstanceIds=['i-06241bd1c4e91c2fc'],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=60);(p/'products-status-command.json').write_text(json.dumps({'command_id':r['Command']['CommandId'],'instance':'i-06241bd1c4e91c2fc'}));print(r['Command']['CommandId'])
