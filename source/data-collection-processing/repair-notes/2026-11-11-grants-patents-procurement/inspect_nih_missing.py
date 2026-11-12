import json
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.worker import load_input
from metadata_engine.evidence import evidence_for
p=Path(__file__).parent;config=json.load(open('config/metadata-engine.json'));db=Database(config);s=db.session.client('s3');out={}
with db.tx()as c:c.execute("SELECT * FROM engine_jobs WHERE source_key='nih_reporter' AND state='retry' AND reason LIKE 'NoSuchKey:%%' LIMIT 1");j=c.fetchone()
if not j:print('No remaining missing-object job');raise SystemExit(0)
class Reader:
 def get_object(self,**kw):
  try:return s.get_object(**kw)
  except Exception as e:out.update(missing_key=kw['Key'],error=type(e).__name__);raise
r=Reader();out['job']={k:j[k]for k in ('job_id','input_key','input_format','reason')}
try:
 rows,_,_=load_input(r,config['bucket'],j,db);offset=int(j['input_format'].split('@')[1])if'@'in j['input_format']else 0
 for row in rows[offset:offset+32]:out['record_id']=row['source_record_id'];evidence_for(row,config['contracts']['nih_reporter'],r,config['bucket'])
 out['revalidation']='passed'
except Exception as e:out['revalidation']=str(e)[:250]
(p/'nih-missing-object.json').write_text(json.dumps(out,indent=2));print(out)
