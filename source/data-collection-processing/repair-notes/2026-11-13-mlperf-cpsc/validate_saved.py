"""Bounded read-only replay of failed and fresh rows against original bytes."""
import io,json,hashlib
from collections import Counter
from metadata_engine.evidence import evidence_for
from metadata_engine.runtime_db import Database

config=json.load(open('config/metadata-engine.json'));db=Database(config);s=db.session.client('s3');bucket=config['bucket']
before=json.loads(s.get_object(Bucket=bucket,Key='research-data/constellation-backfill/repairs/mlperf-cpsc-20261113/before.json')['Body'].read())
cache={}
class Cached:
 def get_object(self,**kw):
  key=kw['Key']
  if key not in cache:
   r=s.get_object(**kw)
   try:cache[key]=r['Body'].read()
   finally:r['Body'].close()
  return {'Body':io.BytesIO(cache[key]),'ContentLength':len(cache[key])}
reader=Cached();out=[]
for source,d in before.items():
 for job in d['failed_jobs']+d['native_jobs'][:2]:
  if job['state']=='uncommitted':continue
  try:
   body=reader.get_object(Bucket=bucket,Key=job['input_key'])['Body'].read();rows=[json.loads(l)for l in body.splitlines()]
   offset=int(job['input_format'].split('@')[1])if'@'in job['input_format']else 0;kinds=Counter()
   selected=rows[offset:offset+32]if'@'in job['input_format']else rows
   for row in selected:
    a=evidence_for(row,config['contracts'][source],reader,bucket);kinds[a[0]['validation']['record_type']]+=1
   entry={'source':source,'job_id':job['job_id'],'input_key':job['input_key'],'verified_rows':sum(kinds.values()),'record_types':dict(kinds),'status':'verified'}
  except Exception as e:entry={'source':source,'job_id':job['job_id'],'status':'failed','reason':type(e).__name__+':'+str(e)}
  out.append(entry);print(json.dumps(entry),flush=True)
key='research-data/constellation-backfill/repairs/mlperf-cpsc-20261113/failed-batch-validation.json'
s.put_object(Bucket=bucket,Key=key,Body=json.dumps(out).encode(),ServerSideEncryption='AES256')
if any(r['status']!='verified'for r in out):raise SystemExit(2)
