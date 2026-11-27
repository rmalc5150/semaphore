import sys
sys.path.insert(0,'/opt/constellation/metadata-engine-runtime')
import json,time
from collections import Counter
from metadata_engine.runtime_db import Database
from metadata_engine.reviewed_continuation import claim
from metadata_engine.worker import process
from metadata_engine.streaming_worker import claim as claim_streaming
from metadata_engine.controller import publish
from metadata_engine.streaming import session as streaming
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');base='research-data/constellation-backfill/repairs/entries-76-90-20261116/';migration=json.loads(s.get_object(Bucket=cfg['bucket'],Key=base+'migration.json')['Body'].read());sources=list(migration['targets']);processed=Counter();errors=[];published={};started=time.monotonic()
def save():
 out={'processed':dict(processed),'published':published,'errors':errors,'elapsed_seconds':round(time.monotonic()-started,2)}
 with db.tx()as c:
  out['sources']={}
  for source in sources:
   c.execute('SELECT state,contract_version,consecutive_raw_failures,last_reason FROM engine_sources WHERE source_key=%s',(source,));entry={'control':c.fetchone()}
   c.execute("SELECT state,count(*) jobs FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s GROUP BY state",(source,));entry['counts']=c.fetchall();out['sources'][source]=entry
 s.put_object(Bucket=cfg['bucket'],Key=base+'replay-publication.json',Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256');print(json.dumps(out,default=str),flush=True)
for _ in range(3):
 for source in sources:
  if time.monotonic()-started>520:break
  try:
   job=claim_streaming(db,source)or claim(db,source)
   if job:
    with streaming():process(db,s,cfg,job)
    processed[source]+=1
   published.setdefault(source,[]).append(publish(db,source_key=source))
  except Exception as e:errors.append({'source':source,'error':type(e).__name__+':'+str(e)[:500]})
 save()
