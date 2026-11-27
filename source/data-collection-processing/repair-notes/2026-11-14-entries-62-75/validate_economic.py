import io,json
from collections import Counter
from metadata_engine.runtime_db import Database
from metadata_engine.evidence import evidence_for
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');b=cfg['bucket'];base='research-data/constellation-backfill/repairs/entries-62-75-20261114/'
before=json.loads(s.get_object(Bucket=b,Key=base+'before.json')['Body'].read());policies=json.loads(s.get_object(Bucket=b,Key=base+'policies.json')['Body'].read());cache={}
class Reader:
 def get_object(self,**kw):
  key=kw['Key']
  if key not in cache:
   r=s.get_object(**kw)
   try:body=r['Body'].read(32*1024*1024+1)
   finally:r['Body'].close()
   assert len(body)<=32*1024*1024
   if sum(map(len,cache.values()))+len(body)>64*1024*1024:cache.clear()
   cache[key]=body
  return {'Body':io.BytesIO(cache[key]),'ContentLength':len(cache[key])}
reader=Reader();results=[];seen=set()
for source in policies:
 with db.tx()as c:
  c.execute("SELECT * FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s AND state='raw_failed' LIMIT 50",(source,));failed=c.fetchall()
 for job in failed+before[source]['native_jobs'][:2]:
  if job['job_id']in seen or not job['input_format'].startswith('legacy_batch'):continue
  seen.add(job['job_id'])
  try:
   body=reader.get_object(Bucket=b,Key=job['input_key'])['Body'].read();rows=[json.loads(l)for l in body.splitlines()if l.strip()]
   offset=int(job['input_format'].split('@')[1])if'@'in job['input_format']else 0
   selected=rows[offset:offset+32]if'@'in job['input_format']else rows;kinds=Counter()
   for row in selected:
    artifacts=evidence_for(row,policies[source],reader,b);kinds[artifacts[0]['validation']['record_type']]+=1
   result={'source':source,'job_id':job['job_id'],'previous_state':job['state'],'status':'verified','rows':sum(kinds.values()),'record_types':dict(kinds)}
  except Exception as error:result={'source':source,'job_id':job['job_id'],'previous_state':job['state'],'status':'failed','reason':type(error).__name__+':'+str(error)}
  results.append(result);print(json.dumps(result),flush=True)
s.put_object(Bucket=b,Key=base+'economic-validation.json',Body=json.dumps(results).encode(),ServerSideEncryption='AES256')
assert all(r['status']=='verified'for r in results),results
