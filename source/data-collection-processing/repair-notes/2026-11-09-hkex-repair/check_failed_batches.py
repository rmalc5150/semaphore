import json,io,time
from pathlib import Path
import boto3
from metadata_engine.runtime_db import Database
from metadata_engine.hkex_documents import Client,expand
from metadata_engine.evidence import evidence_for
from metadata_engine.labelling import label_observation
p=Path(__file__).parent;config=json.load(open('config/metadata-engine.json'));db=Database(config);s=db.session.client('s3');bucket=config['bucket'];contract=config['contracts']['hkex_news'];out=[];cache={}
class Cached:
 def get_object(self,**args):
  key=args['Key']
  if key not in cache:
   r=s.get_object(**args);cache[key]=r['Body'].read();r['Body'].close()
  return {'Body':io.BytesIO(cache[key]),'ContentLength':len(cache[key])}
read=Cached()
with db.tx() as c:
 c.execute("SELECT job_id,input_key,input_format FROM engine_jobs WHERE source_key='hkex_news' AND state='raw_failed'");jobs=c.fetchall()
for job in jobs:
 raw=read.get_object(Bucket=bucket,Key=job['input_key'])['Body'].read();rows=[json.loads(line)for line in raw.splitlines()];offset=int(job['input_format'].split('@')[1])if'@'in job['input_format']else 0
 client=Client(s,bucket,max_requests=30);result={'job_id':job['job_id'],'input_rows':min(32,len(rows)-offset),'originals_verified':0,'language_notices':[]}
 try:
  for original in rows[offset:offset+32]:
   expanded,gap=expand(original,client,read,bucket)
   if gap:result['language_notices'].append(gap)
   for record,envelope in expanded:
    artifacts=evidence_for(record,contract,read,bucket)
    envelope=envelope or{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+job['input_key'],'sha256':__import__('hashlib').sha256(raw).hexdigest(),'origin':'first_party_source'}
    label_observation({**record,'raw_s3_uri':envelope['s3_uri'],'raw_sha256':envelope['sha256'],'raw_completeness_status':'complete','raw_artifacts':[envelope,*artifacts]},contract)
    result['originals_verified']+=1
  result['status']='passed'
 except Exception as e:result.update(status='failed',error_type=type(e).__name__,reason=str(e))
 out.append(result);(p/'failed-batch-validation.json').write_text(json.dumps(out,indent=2));print(json.dumps(result),flush=True)
if not out or any(r['status']!='passed'for r in out):raise SystemExit(1)
