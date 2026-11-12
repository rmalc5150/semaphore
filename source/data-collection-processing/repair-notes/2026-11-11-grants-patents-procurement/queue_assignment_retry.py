import json
from pathlib import Path
from metadata_engine.runtime_db import Database
p=Path(__file__).parent;db=Database(json.load(open('config/metadata-engine.json')))
with db.tx()as c:
 c.execute("SELECT job_id,state,reason FROM engine_jobs WHERE source_key='uspto_odp' AND contract_version='2.0.3' AND state='raw_failed' AND reason='patent_application_mapping_differs_from_original'");old=c.fetchall();(p/'assignment-retry-before.json').write_text(json.dumps(old,indent=2,default=str))
 for j in old:c.execute("UPDATE engine_jobs SET state='retry',available_after=UTC_TIMESTAMP(6) WHERE job_id=%s AND state='raw_failed'",(j['job_id'],))
print(old)
