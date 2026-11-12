import json
from pathlib import Path
from metadata_engine.runtime_db import Database,collection_tx
p=Path(__file__).parent;db=Database(json.load(open('config/metadata-engine.json')));out={}
with collection_tx(db.session,db.config,role='controller')as c:
 for source in ('nih_reporter','usa_spending','ted_notices'):
  key='legacy:constellation-specialist-'+source+'.service';c.execute("SELECT /*+ MAX_EXECUTION_TIME(5000) */ job_id,status,attempts,FROM_UNIXTIME(updated_at) updated_at,result_json FROM backfill_jobs WHERE source_key=%s ORDER BY updated_at DESC LIMIT 2",(key,));out[source]=c.fetchall()
(p/'historical-routes.json').write_text(json.dumps(out,indent=2,default=str));print(json.dumps(out,default=str)[:4000])
