import json
from pathlib import Path
from metadata_engine.runtime_db import Database,fingerprint
from metadata_engine.controller import register_contract
p=Path(__file__).parent;config=json.load(open('config/metadata-engine.json'));db=Database(config);policy=config['contracts']['finlight']
with db.tx()as c:
 c.execute("SELECT * FROM engine_jobs WHERE source_key='finlight' AND state IN ('queued','retry','raw_failed')");old=c.fetchall();(p/'jobs-before-migration.json').write_text(json.dumps(old,indent=2,default=str));register_contract(db,policy,c);new=[];repairs=[]
 for j in old:
  db.enqueue('finlight',j['input_key'],j['input_etag'],j['input_format'],200 if j['state']=='raw_failed'else j['priority'],c)
  identity=fingerprint(['finlight',j['input_key'],j['input_etag'],j['input_format'],policy['contract_version']]);new.append(identity)
  if j['state']=='raw_failed':repairs.append(identity)
  c.execute("UPDATE engine_jobs SET state='superseded',reason='requeued_under_finlight_native_response_contract_2.0.3' WHERE job_id=%s AND state IN ('queued','retry','raw_failed')",(j['job_id'],))
 c.execute("UPDATE engine_sources SET state='enabled',consecutive_raw_failures=0,last_reason=NULL,updated_at=UTC_TIMESTAMP(6) WHERE source_key='finlight' AND state='raw_stopped'")
s=db.session.client('s3');today=s.list_objects_v2(Bucket=config['bucket'],Prefix='research-data/raw/source=finlight/dataset=news_articles/ingestion_date=2026-11-09/',MaxKeys=1).get('Contents',[])
for item in today:
 db.enqueue('finlight',item['Key'],item['ETag'],'legacy_batch',190);repairs.append(fingerprint(['finlight',item['Key'],item['ETag'],'legacy_batch',policy['contract_version']]))
(p/'migration.json').write_text(json.dumps({'migrated_jobs':len(new),'repair_job_ids':repairs,'contract_version':policy['contract_version']},indent=2));print('Migrated',len(new),'jobs; prioritized',len(repairs),'repairs/current-capture checks.')
