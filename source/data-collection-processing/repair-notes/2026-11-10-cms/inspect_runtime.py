import json,boto3,time
from pathlib import Path
p=Path(__file__).parent;c=json.load(open('config/constellation-infrastructure.json'));s=boto3.client('ssm',region_name=c['region']);cmd="systemctl list-units 'constellation-*' 'optima-specialist*' --no-pager; systemctl cat constellation-specialist-cms_coverage.service; journalctl -u constellation-legacy-worker@1.service -u constellation-legacy-worker@2.service -n 8 --no-pager; systemctl show optima-specialist-daily.service optima-specialist-historical.service -p ActiveState -p Result -p ExecMainStatus"
r=s.send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=60);ref={'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id']};(p/'runtime-command.json').write_text(json.dumps(ref))
for _ in range(50):
 try:o=s.get_command_invocation(CommandId=ref['command_id'],InstanceId=ref['instance'])
 except s.exceptions.InvocationDoesNotExist:time.sleep(1);continue
 if o['Status']not in ('Pending','InProgress','Delayed'):break
 time.sleep(1)
(p/'runtime-result.json').write_text(json.dumps(o,indent=2,default=str));print(o['StandardOutputContent'],o['StandardErrorContent'])
from metadata_engine.runtime_db import Database
db=Database(json.load(open('config/metadata-engine.json')))
with db.tx()as x:
 x.execute("SELECT * FROM engine_jobs WHERE source_key='cms_coverage_documents' AND input_format='public_receipt' LIMIT 1");j=x.fetchone()
 if j:
  raw=db.session.client('s3').get_object(Bucket=c['bucket'],Key=j['input_key'])['Body'].read();(p/'sample-public-receipt.jsonl').write_bytes(raw);print('PUBLIC',raw[:3000].decode())
