import json,hashlib
from pathlib import Path
from constellation.finish_aux_migration import remote,T3,M7,session
P=Path(__file__).parent;B='data-collection-059416028963-us-east-1-an';s=session.client('s3');proof=json.loads((P/'failed-batch-validation.json').read_text());failed={j['job_id']for d in json.loads((P/'before.json').read_text()).values()for j in d['failed_jobs']if j['state']=='raw_failed'};assert all(r['status']=='verified'for r in proof if r['job_id']in failed)
policies=json.loads((P/'policies.json').read_text())
remote(T3,'''import json,time
from pathlib import Path
from metadata_engine.runtime_db import Database,fingerprint
from metadata_engine.controller import register_contract
cfg_path=Path('config/metadata-engine.json');cfg=json.loads(cfg_path.read_text());policies=POLICIES
for source,policy in policies.items():cfg['contracts'][source]=policy;cfg.setdefault('verified_source_failure_handling',{})[source]='queue_by_source_date'
tmp=cfg_path.with_suffix('.repair.tmp');tmp.write_text(json.dumps(cfg,indent=2)+'\\n');tmp.replace(cfg_path)
db=Database(cfg);s=db.session.client('s3');migrated=[]
with db.tx()as c:
 for source,policy in policies.items():
  c.execute("SELECT * FROM engine_jobs WHERE source_key=%s AND contract_version<>%s AND state IN ('queued','retry','raw_failed') FOR UPDATE",(source,policy['contract_version']));old=c.fetchall()
  c.execute("SELECT 1 FROM engine_jobs WHERE source_key=%s AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1",(source,));assert not c.fetchone(),'source already running; do not race migration'
  key='research-data/constellation-backfill/repairs/comtrade-doe-20261113/jobs-before-'+source+'.json'
  s.put_object(Bucket=cfg['bucket'],Key=key,Body=json.dumps(old,default=str).encode(),ServerSideEncryption='AES256')
  register_contract(db,policy,c)
  c.execute('UPDATE engine_sources SET catalog_entries=%s WHERE source_key=%s',(json.dumps(policy['catalog_entries']),source))
  for j in old:
   priority=450 if j['state']=='raw_failed' else 425 if j['state']=='retry' else 400 if '/ingestion_date=2026-11-'in j['input_key']else 200
   db.enqueue(source,j['input_key'],j['input_etag'],j['input_format'],priority,c)
   new=fingerprint([source,j['input_key'],j['input_etag'],j['input_format'],policy['contract_version']])
   c.execute("UPDATE engine_jobs SET state='superseded',reason='requeued_under_verified_original_contract_2.0.3',finished_at=UTC_TIMESTAMP(6) WHERE job_id=%s AND state IN ('queued','retry','raw_failed')",(j['job_id'],))
   migrated.append({'source':source,'old_job_id':j['job_id'],'new_job_id':new,'previous_state':j['state']})
  c.execute("UPDATE engine_sources SET state='enabled',consecutive_raw_failures=0,last_reason=NULL,updated_at=UTC_TIMESTAMP(6) WHERE source_key=%s AND state='raw_stopped'",(source,))
key='research-data/constellation-backfill/repairs/comtrade-doe-20261113/migration.json';s.put_object(Bucket=cfg['bucket'],Key=key,Body=json.dumps(migrated).encode(),ServerSideEncryption='AES256');print(json.dumps({'migrated':len(migrated),'key':key}))
'''.replace('POLICIES',repr(policies)))
raw=(P/'replay_publish.py').read_bytes();sha=hashlib.sha256(raw).hexdigest();key='research-data/constellation-backfill/deployments/comtrade-doe-20261113/'+sha+'/replay_publish.py';s.put_object(Bucket=B,Key=key,Body=raw,ServerSideEncryption='AES256')
remote(M7,'''import boto3,hashlib,subprocess,os
from pathlib import Path
raw=boto3.client('s3',region_name='us-east-1').get_object(Bucket=BUCKET,Key=KEY)['Body'].read();assert hashlib.sha256(raw).hexdigest()==SHA
p=Path('/opt/constellation/metadata-engine-runtime/replay_comtrade_doe.py');p.write_bytes(raw);os.chown(p,1000,1000)
subprocess.run(['systemd-run','--unit=optima-comtrade-doe-replay-20261113','--no-block','--collect','--property=User=ec2-user','--property=WorkingDirectory=/opt/constellation/metadata-engine-runtime','--property=Slice=constellation-workers.slice','--property=MemoryMax=1G','--property=CPUQuota=50%','--property=RuntimeMaxSec=900','/opt/constellation/legacy-venv/bin/python','-B',str(p)],check=True)
print('Started fenced replay/publication on m7')
'''.replace('BUCKET',repr(B)).replace('KEY',repr(key)).replace('SHA',repr(sha)))
