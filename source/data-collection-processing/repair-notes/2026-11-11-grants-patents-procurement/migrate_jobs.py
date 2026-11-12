import json
from pathlib import Path
from metadata_engine.runtime_db import Database,fingerprint
from metadata_engine.controller import register_contract
p=Path(__file__).parent;config=json.load(open('config/metadata-engine.json'));db=Database(config)
sources=json.loads((p/'sources.json').read_text());summary={}
for source in sources:
 policy=config['contracts'][source]
 with db.tx() as c:
  c.execute("SELECT * FROM engine_jobs WHERE source_key=%s AND contract_version<>%s AND state IN ('queued','retry','raw_failed') AND (input_format LIKE 'legacy_batch%%' OR input_format='public_receipt')",(source,policy['contract_version']));old=c.fetchall()
  (p/source).mkdir(exist_ok=True);(p/source/'jobs-before-migration.json').write_text(json.dumps(old,indent=2,default=str));register_contract(db,policy,c);new=[];repairs=[]
  values=[]
  for j in old:
   identity=fingerprint([source,j['input_key'],j['input_etag'],j['input_format'],policy['contract_version']]);new.append(identity)
   values.append((identity,source,j['input_key'],j['input_etag'],j['input_format'],policy['contract_version'],200 if j['state']=='raw_failed' else j['priority']))
   if j['state']=='raw_failed':repairs.append(identity)
  for offset in range(0,len(values),250):
   c.executemany("INSERT IGNORE INTO engine_jobs(job_id,source_key,input_key,input_etag,input_format,contract_version,priority,available_after,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))",values[offset:offset+250])
   ids=tuple(j['job_id']for j in old[offset:offset+250])
   c.execute("UPDATE engine_jobs SET state='superseded',reason='source_specific_original_validation_2.0.3' WHERE job_id IN %s AND state IN ('queued','retry','raw_failed')",(ids,))
  c.execute("UPDATE engine_sources SET state='enabled',consecutive_raw_failures=0,last_reason=NULL,updated_at=UTC_TIMESTAMP(6) WHERE source_key=%s AND state='raw_stopped'",(source,))
 prior=json.loads((p/source/'migration.json').read_text()) if (p/source/'migration.json').exists() else {}
 summary[source]={'migrated_jobs':len(new),'repair_job_ids':list(dict.fromkeys(prior.get('repair_job_ids',[])+repairs)),'contract_version':policy['contract_version']}
 (p/source/'migration.json').write_text(json.dumps(summary[source],indent=2));print(source,len(new),len(repairs),flush=True)
(p/'migration.json').write_text(json.dumps(summary,indent=2))
