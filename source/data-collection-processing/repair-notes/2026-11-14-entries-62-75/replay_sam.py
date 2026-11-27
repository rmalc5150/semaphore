import json
from metadata_engine.runtime_db import Database
from metadata_engine.reviewed_continuation import claim
from metadata_engine.worker import process
from metadata_engine.controller import publish
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');base='research-data/constellation-backfill/repairs/entries-62-75-20261114/';b=cfg['bucket'];processed=[]
for _ in range(5):
 job=claim(db,'sam_gov_opportunities')
 if not job:break
 process(db,s,cfg,job);processed.append(job['job_id'])
migrated=json.loads(s.get_object(Bucket=b,Key=base+'sam-migration.json')['Body'].read());ids=[r['new']for r in migrated if r['state']=='raw_failed'];rows=[]
with db.tx()as c:
 for identity in ids:
  c.execute('SELECT job_id,state,output_rows,reason FROM engine_jobs WHERE job_id=%s',(identity,));rows.append(c.fetchone())
accepted=[r['job_id']for r in rows if r['state']=='accepted'];published=publish(db,source_key='sam_gov_opportunities',job_ids=accepted)if accepted else 0
out={'processed':processed,'repaired_jobs':rows,'published':published};s.put_object(Bucket=b,Key=base+'sam-replay.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print(json.dumps(out))
