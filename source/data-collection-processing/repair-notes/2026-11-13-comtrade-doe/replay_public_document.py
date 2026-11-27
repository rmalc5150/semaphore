"""Verify a saved public-archive storage report through the normal leased worker."""
import json,time
from metadata_engine.runtime_db import Database
from metadata_engine.reviewed_continuation import claim
from metadata_engine.worker import process
from metadata_engine.controller import publish
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3')
base='research-data/constellation-backfill/repairs/comtrade-doe-20261113/'
selection=json.loads(s.get_object(Bucket=cfg['bucket'],Key=base+'public-scope-reconciliation.json')['Body'].read())
identity=selection['storage_document_job_ids'][0];started=time.monotonic();worked=[]
while time.monotonic()-started<120:
 with db.tx()as c:
  c.execute('SELECT state FROM engine_jobs WHERE job_id=%s',(identity,));state=c.fetchone()['state']
 if state=='accepted':break
 job=claim(db,'doe_storage_program')
 if job:process(db,s,cfg,job);worked.append(job['job_id'])
 else:time.sleep(2)
with db.tx()as c:
 c.execute('SELECT job_id,state,reason,output_rows,output_uri FROM engine_jobs WHERE job_id=%s',(identity,));verified=c.fetchone()
assert verified['state']=='accepted',verified
published=publish(db,source_key='doe_storage_program',job_ids=[identity])
out={'selected_document':verified,'jobs_processed':worked,'published_batches':published,'elapsed_seconds':round(time.monotonic()-started,2)}
s.put_object(Bucket=cfg['bucket'],Key=base+'public-document-verified.json',Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256')
print(json.dumps(out,default=str),flush=True)
