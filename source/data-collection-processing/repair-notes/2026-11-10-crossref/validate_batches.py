import json,io
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.evidence import evidence_for
p=Path(__file__).parent;config=json.load(open('config/metadata-engine.json'));contract=config['contracts']['crossref_proceedings'];db=Database(config);s=db.session.client('s3');cache={}
class Cache:
 def get_object(self,**kw):
  key=kw['Key']
  if key not in cache:
   r=s.get_object(**kw);cache[key]=r['Body'].read();r['Body'].close()
  return {'Body':io.BytesIO(cache[key]),'ContentLength':len(cache[key])}
reader=Cache();out=[]
with db.tx()as c:
 c.execute("SELECT * FROM engine_jobs WHERE source_key='crossref_proceedings' AND state='raw_failed'");jobs=c.fetchall()
(p/'failed-jobs-before.json').write_text(json.dumps(jobs,indent=2,default=str))
for j in jobs:
 raw=reader.get_object(Bucket=config['bucket'],Key=j['input_key'])['Body'].read();rows=[json.loads(l)for l in raw.splitlines()];offset=int(j['input_format'].split('@')[1])if'@'in j['input_format']else 0;count=0
 for r in rows[offset:offset+32]:
  artifacts=evidence_for(r,contract,reader,config['bucket']);assert any(a['artifact_kind']=='provider_record'and a.get('validation',{}).get('provider')=='Crossref proceedings metadata'for a in artifacts);count+=1
 out.append({'job_id':j['job_id'],'verified_rows':count});print(out[-1],flush=True)
(p/'failed-batch-validation.json').write_text(json.dumps(out,indent=2))
