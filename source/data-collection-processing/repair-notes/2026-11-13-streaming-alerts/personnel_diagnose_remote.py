import os,sys,json
os.chdir('/opt/constellation/metadata-engine-runtime');sys.path.insert(0,os.getcwd())
from metadata_engine.runtime_db import Database
c=json.load(open('config/metadata-engine.json'));d=Database(c);s=d.session.client('s3')
with d.tx()as x:
 x.execute("SELECT job_id,state,reason,report_uri FROM engine_jobs WHERE job_id='7320999dc6740ae6106f5e26b38c80ed36e7c79cf6506d2e7b90dbafdb2f3e12'");r=x.fetchone()
print(json.dumps(r),flush=True)
if r['report_uri']:
 key=r['report_uri'].split('/',3)[3];print(s.get_object(Bucket=c['bucket'],Key=key)['Body'].read().decode()[:5500])
with d.tx()as x:
 x.execute("SELECT state,last_reason FROM engine_sources WHERE source_key='european_commission_cordis'");print(json.dumps(x.fetchone()))
