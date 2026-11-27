import json,time
from collections import Counter
from metadata_engine.runtime_db import Database
from metadata_engine.reviewed_continuation import claim
from metadata_engine.worker import process
from metadata_engine.controller import publish

cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');started=time.monotonic();processed=Counter();publications={}
for _ in range(6):
 for source in ('federal_register','federal_register_documents'):
  if time.monotonic()-started>210:break
  job=claim(db,source)
  if job:process(db,s,cfg,job);processed[source]+=1
for source in ('federal_register','federal_register_documents'):
 publications[source]=[publish(db,source_key=source)]
 if publications[source][0]==5:publications[source].append(publish(db,source_key=source))
out={'processed':dict(processed),'published_batches':publications,'sources':{},'elapsed_seconds':round(time.monotonic()-started,2)}
with db.tx()as q:
 for source in ('federal_register','federal_register_documents'):
  q.execute('SELECT source_key,state,contract_version,consecutive_raw_failures,last_reason FROM engine_sources WHERE source_key=%s',(source,));entry={'control':q.fetchone()}
  q.execute('SELECT state,count(*) AS jobs,sum(output_rows) AS output_rows FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s GROUP BY state',(source,));entry['counts']=q.fetchall()
  q.execute("SELECT job_id,output_rows,output_uri FROM engine_jobs WHERE source_key=%s AND state='accepted' ORDER BY finished_at DESC LIMIT 10",(source,));entry['accepted']=q.fetchall();out['sources'][source]=entry
key='research-data/constellation-backfill/repairs/federal-register-20261113/replay-publication.json';s.put_object(Bucket=cfg['bucket'],Key=key,Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256');print(json.dumps(out,default=str),flush=True)
