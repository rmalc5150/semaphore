import json
from pathlib import Path
from metadata_engine.runtime_db import Database,fingerprint
from metadata_engine.controller import register_contract
p=Path(__file__).parent;config=json.load(open('config/metadata-engine.json'));db=Database(config);policy=config['contracts']['uk_mhra']
with db.tx()as c:
 c.execute("SELECT * FROM engine_jobs WHERE source_key='uk_mhra' AND state IN ('queued','retry','raw_failed')");old=c.fetchall();(p/'jobs-before-migration.json').write_text(json.dumps(old,indent=2,default=str));register_contract(db,policy,c);new=[];repairs=[]
 for j in old:
  db.enqueue('uk_mhra',j['input_key'],j['input_etag'],j['input_format'],200 if j['state']=='raw_failed'else j['priority'],c)
  identity=fingerprint(['uk_mhra',j['input_key'],j['input_etag'],j['input_format'],policy['contract_version']]);new.append(identity)
  if j['state']=='raw_failed':repairs.append(identity)
  c.execute("UPDATE engine_jobs SET state='superseded',reason='requeued_under_uk_mhra_native_response_contract_2.0.3' WHERE job_id=%s AND state IN ('queued','retry','raw_failed')",(j['job_id'],))
 c.execute("UPDATE engine_sources SET state='enabled',consecutive_raw_failures=0,last_reason=NULL,updated_at=UTC_TIMESTAMP(6) WHERE source_key='uk_mhra' AND state='raw_stopped'")

(p/'migration.json').write_text(json.dumps({'migrated_jobs':len(new),'repair_job_ids':list(dict.fromkeys(repairs)),'contract_version':policy['contract_version']},indent=2));print('Migrated',len(new),'jobs; selected',len(set(repairs)),'replays.')
