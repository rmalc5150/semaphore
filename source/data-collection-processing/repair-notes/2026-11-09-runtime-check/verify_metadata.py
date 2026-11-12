import json
from pathlib import Path
from metadata_engine.runtime_db import Database
p=Path(__file__).parent;db=Database(json.load(open('config/metadata-engine.json')));out={'status':db.stats()}
with db.tx() as c:
 c.execute('SELECT source_key,state,consecutive_raw_failures,last_reason FROM engine_sources WHERE source_key=%s',('sec_companyfacts',));out['sec_companyfacts']=c.fetchone()
 c.execute('SELECT state,COUNT(*) n,SUM(output_rows) output_rows FROM engine_jobs WHERE source_key=%s GROUP BY state',('sec_companyfacts',));out['sec_companyfacts_jobs']=c.fetchall()
 c.execute("SELECT source_key,state,finished_at,output_rows FROM engine_jobs WHERE state='accepted' ORDER BY finished_at DESC LIMIT 5");out['latest_accepted']=c.fetchall()
(p/'metadata-after.json').write_text(json.dumps(out,indent=2,default=str));print(json.dumps({k:v for k,v in out.items() if k!='status'},default=str));print('Job counts',out['status']['jobs']);print('Held source count',len(out['status']['restricted_sources']))
