import json,boto3,time
from pathlib import Path
p=Path(__file__).parent;wanted=('nih','nist','spending','ted','assignment','patent')
for r in json.load(open('config/constellation-legacy-routes.json'))['routes']:
 if any(s in r.get('unit','')for s in wanted):print('ROUTE',r['unit'],r.get('execution_enabled'),r.get('cadence_seconds'))
from metadata_engine.runtime_db import Database
c=json.load(open('config/metadata-engine.json'));db=Database(c)
with db.tx()as x:
 x.execute("SELECT * FROM engine_sources WHERE source_key LIKE 'nist_robotics%%'");print('NIST',x.fetchall())
 x.execute("SELECT input_key,input_etag,input_format,state FROM engine_jobs WHERE source_key='nist_robotics_documents' AND input_format LIKE 'legacy_batch%%' LIMIT 1");j=x.fetchone()
 if j:
  r=json.loads(db.session.client('s3').get_object(Bucket=c['bucket'],Key=j['input_key'])['Body'].read().splitlines()[0]);(p/'nist_robotics_methods/sample-document-record.json').write_text(json.dumps(r,indent=2));print('NIST DOC',r['source_record_id'],r['source_url'],r['payload'].get('data',{}).get('kind'),list(r['payload']))
s=boto3.client('ssm',region_name='us-east-1');cmd="systemctl list-timers '*nih*' '*grant*' '*nist*' '*patent*' '*specialist*' --all --no-pager; systemctl --failed --no-pager"
r=s.send_command(InstanceIds=['i-06241bd1c4e91c2fc'],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=60);(p/'routes-command.json').write_text(json.dumps({'command_id':r['Command']['CommandId'],'instance':'i-06241bd1c4e91c2fc'}))
for _ in range(40):
 try:o=s.get_command_invocation(CommandId=r['Command']['CommandId'],InstanceId='i-06241bd1c4e91c2fc')
 except s.exceptions.InvocationDoesNotExist:time.sleep(1);continue
 if o['Status']not in ('Pending','InProgress','Delayed'):break
 time.sleep(1)
(p/'routes-result.json').write_text(json.dumps(o,indent=2,default=str));print(o['StandardOutputContent'])
