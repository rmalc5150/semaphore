import json,subprocess
from pathlib import Path
script=r'''import os,sys,json,fcntl,uuid,time
from pathlib import Path
os.chdir('/opt/constellation/metadata-engine-runtime');sys.path.insert(0,os.getcwd())
from metadata_engine.runtime_db import Database
from metadata_engine.worker import process
from metadata_engine.streaming import session
from metadata_engine.controller import publish
c=json.load(open('config/metadata-engine.json'));db=Database(c);jid='cc1d1f02b206d3599cd6e4b7dc054293b9bd5dcb9b0dfc85ff7c79bf1a92ad40';lock=Path('/opt/constellation/tmp/metadata-streaming-worker.lock').open('a')
fcntl.flock(lock,fcntl.LOCK_EX)
with db.tx()as x:
 x.execute("SELECT state FROM engine_sources WHERE source_key='trade_screening' FOR UPDATE");assert x.fetchone()['state']=='enabled'
 x.execute("SELECT job_id FROM engine_jobs WHERE source_key='trade_screening' AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1")
 if x.fetchone():raise RuntimeError('source_has_active_lease; leave queued rather than overlap')
 x.execute('SELECT * FROM engine_jobs WHERE job_id=%s FOR UPDATE',(jid,));job=x.fetchone()
 if job['state']!='accepted':
  assert job['state']=='retry';token=str(uuid.uuid4());x.execute("UPDATE engine_jobs SET state='running',lease_token=%s,lease_until=DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 20 MINUTE),attempts=attempts+1 WHERE job_id=%s",(token,jid));job['lease_token']=token
if job['state']!='accepted':
 with session():process(db,db.session.client('s3'),c,job)
publish(db,source_key='trade_screening',job_ids=[jid])
a=db.session.client('athena');sql="SELECT count(*) observations,count_if(raw_completeness_status='complete') complete_raw,count_if(json_extract_scalar(labelled_json,'$.source_record_id_basis')='documented_composite') composite_ids FROM optima_metadata_engine.source_observations WHERE job_id='"+jid+"'";q=a.start_query_execution(QueryString=sql,WorkGroup=c['athena_workgroup'])['QueryExecutionId']
for _ in range(45):
 e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
 if state in ('SUCCEEDED','FAILED','CANCELLED'):break
 time.sleep(1)
assert state=='SUCCEEDED',e['Status'];rows=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows'];assert int(rows[1]['Data'][0]['VarCharValue'])>0,rows
result={'job_id':jid,'query_id':q,'sql':sql,'rows':rows};db.session.client('s3').put_object(Bucket=c['bucket'],Key=c['prefix']+'/repair-receipts/streaming-20261113/composite-trade-publication.json',Body=json.dumps(result).encode(),ServerSideEncryption='AES256');print(json.dumps(result),flush=True)
'''
p=Path('/opt/constellation/tmp/verify-trade-composite-1113.py');p.write_text(script);p.chmod(0o644)
cmd=['systemd-run','--wait','--collect','--pipe','--unit=optima-metadata-trade-composite-1113','--property=User=ec2-user','--property=Slice=constellation-workers.slice','--property=MemoryHigh=640M','--property=MemoryMax=768M','--property=CPUQuota=75%','--property=RuntimeMaxSec=300','/opt/constellation/legacy-venv/bin/python','-u','-B',str(p)]
r=subprocess.run(cmd,capture_output=True,text=True);print(r.stdout[-6500:],r.stderr[-1200:],flush=True);assert r.returncode==0
