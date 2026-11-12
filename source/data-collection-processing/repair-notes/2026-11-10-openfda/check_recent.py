import json,io
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.evidence import evidence_for
p=Path(__file__).parent;cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');cache={}
class Cached:
 def get_object(self,**kw):
  key=kw['Key']
  if key not in cache:cache[key]=s.get_object(**kw)['Body'].read()
  return {'Body':io.BytesIO(cache[key]),'ContentLength':len(cache[key])}
reader=Cached()
with db.tx()as c:
 c.execute("SELECT * FROM engine_jobs WHERE source_key='fda_openfda' AND input_format LIKE 'legacy_batch%%' ORDER BY input_key DESC LIMIT 1");jobs=c.fetchall()
assert jobs
j=jobs[0];rows=[json.loads(l)for l in reader.get_object(Bucket=cfg['bucket'],Key=j['input_key'])['Body'].read().splitlines()];checked=rows[:32]
for r in checked:assert evidence_for(r,cfg['contracts']['fda_openfda'],reader,cfg['bucket'])
path=j['input_key'].split('/');key=f"research-data/manifests/collection_runs/source=fda_openfda/dataset=research_records/{path[5].split('=',1)[1]}/final.json";m=json.loads(reader.get_object(Bucket=cfg['bucket'],Key=key)['Body'].read());out={'job':j,'verified_rows':len(checked),'latest_ingested_at':max(r['ingested_at']for r in rows),'manifest':key.removeprefix('research-data/'),'status':m['status'],'exhausted':m.get('exhausted'),'window':m['task'].get('window')};(p/'recent-batch.json').write_text(json.dumps(out,indent=2,default=str));print({k:v for k,v in out.items()if k!='job'})
from constellation.control import Control
c=Control();controls={'daily_allowed':c.daily_allowed(),'historical_allowed':c.allowed()};(p/'collection-controls.json').write_text(json.dumps(controls,indent=2));print(controls)
