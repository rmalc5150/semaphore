import boto3,json
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3',region_name='us-east-1');bucket='data-collection-059416028963-us-east-1-an'
for prefix in ('research-data/operations/runtime/','research-data/constellation-backfill/legacy-runtime/optima-cms-financial-collection.service/','research-data/operations/supervisor/'):
 r=s.list_objects_v2(Bucket=bucket,Prefix=prefix,MaxKeys=30);rows=[(o['Key'],o['Size'])for o in r.get('Contents',[])];print(prefix,rows)
from metadata_engine.runtime_db import Database
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg)
with db.tx()as c:
 c.execute("SELECT * FROM engine_jobs WHERE source_key='cms_payments_catalog' AND input_format='public_receipt' LIMIT 1");j=c.fetchone()
 if j:
  raw=s.get_object(Bucket=bucket,Key=j['input_key'])['Body'].read();(p/'sample-public-receipt.jsonl').write_bytes(raw);print('PUBLIC',raw[:1800].decode())
ssm=boto3.client('ssm',region_name='us-east-1');cmd="systemctl list-timers '*cms*' --all --no-pager; find /opt/constellation -name '*cms-financial*' -o -name '*cms*sqlite3' | head -20; systemctl is-active optima-metadata-worker.timer; systemctl --failed --no-pager"
r=ssm.send_command(InstanceIds=['i-06241bd1c4e91c2fc'],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=60);(p/'runtime-command.json').write_text(json.dumps({'command_id':r['Command']['CommandId'],'instance':'i-06241bd1c4e91c2fc'}));print('SSM',r['Command']['CommandId'])
