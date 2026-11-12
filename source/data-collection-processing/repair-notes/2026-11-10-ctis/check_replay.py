import json
from pathlib import Path
from metadata_engine.runtime_db import Database
p=Path(__file__).parent;db=Database(json.load(open('config/metadata-engine.json')));ids=tuple(json.loads((p/'migration.json').read_text())['repair_job_ids'])
with db.tx()as c:
 c.execute('SELECT job_id,input_format,state,reason,output_rows FROM engine_jobs WHERE job_id IN %s',(ids,));rows=c.fetchall()
assert len(rows)==len(ids)
for r in rows:
 if r['input_format'].startswith('legacy_batch'):assert r['state']=='accepted' and r['output_rows']>0,r
 else:assert r['state']=='raw_failed' and r['reason']=='public_capture_is_discovery_page_only',r
(p/'replay-verified.json').write_text(json.dumps({'status':'passed','results':rows},indent=2));print('Verified accepted native batches and isolated discovery-page gaps:',len(rows))
