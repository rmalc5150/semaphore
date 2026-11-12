import json,time
from pathlib import Path
from metadata_engine.runtime_db import Database
p=Path(__file__).parent;db=Database(json.load(open('config/metadata-engine.json')));ids=tuple(json.load(open(p/'fresh-replay.json'))['repair_job_ids'])
for _ in range(30):
 with db.tx()as c:c.execute('SELECT job_id,state,reason,output_rows FROM engine_jobs WHERE job_id IN %s',(ids,));rows=c.fetchall()
 if all(r['state']=='accepted'for r in rows):print(json.dumps(rows),flush=True);(p/'fresh-job-result.json').write_text(json.dumps(rows,indent=2));break
 if any(r['state']=='raw_failed'for r in rows):raise RuntimeError(rows)
 time.sleep(2)
else:print('Still queued/running; source lease preserved.',rows,flush=True)
