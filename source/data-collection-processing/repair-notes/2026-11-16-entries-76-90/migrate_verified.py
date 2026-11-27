from ops import *
code='''import json
from pathlib import Path
from metadata_engine.runtime_db import Database,fingerprint
from metadata_engine.controller import register_contract
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');bucket=cfg['bucket'];base=BASE
proof=json.loads(s.get_object(Bucket=bucket,Key=base+'capture-proof.json')['Body'].read());policies=json.loads(s.get_object(Bucket=bucket,Key=base+'policies.json')['Body'].read());out={'sources':{},'targets':{}}
for source,policy in policies.items():
 if source in proof['public']:assert proof['public'][source]['status']=='verified',source
 elif source=='arxiv':assert len(proof[source])==4 and all(v['status']=='verified'for v in proof[source])
 else:assert all(proof['native'][m]['verified_rows']>=1000 for m in ('historical','daily'))
 with db.tx()as c:
  c.execute("SELECT state FROM engine_sources WHERE source_key=%s FOR UPDATE",(source,));control=c.fetchone();assert control['state']not in ('owner_paused','access_layer')
  c.execute("SELECT job_id FROM engine_jobs WHERE source_key=%s AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1",(source,));running=c.fetchone()
  if running:out['sources'][source]={'deferred_active_job':running};continue
  c.execute("SELECT * FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s AND state IN ('queued','retry','raw_failed') AND contract_version<>%s FOR UPDATE",(source,policy['contract_version']));old=c.fetchall()
  s.put_object(Bucket=bucket,Key=base+'jobs-before-'+source+'.json',Body=json.dumps(old,default=str).encode(),ServerSideEncryption='AES256')
  register_contract(db,policy,c)
  for job in old:
   if source=='arxiv':db.enqueue(source,job['input_key'],job['input_etag'],job['input_format'],450 if job['state']=='raw_failed'else 200,c)
  c.execute("UPDATE engine_jobs SET state='superseded',reason=%s,finished_at=UTC_TIMESTAMP(6) WHERE source_key=%s AND state IN ('queued','retry','raw_failed') AND contract_version<>%s",('requeued_native_abstract_contract_2.0.3'if source=='arxiv'else'legacy_public_contract_retired; native_scope_rediscovery',source,policy['contract_version']))
  c.execute("UPDATE engine_sources SET state='enabled',consecutive_raw_failures=0,last_reason=NULL,updated_at=UTC_TIMESTAMP(6) WHERE source_key=%s AND state='raw_stopped'",(source,))
  refs=[]
  if source in proof['public']:
   p=proof['public'][source];refs=[(r['receipt_key'],'public_receipt')for r in p.get('results',[p])if r.get('status')=='verified']
  elif source=='arxiv':refs=[(j['input_key'],next(v['input_format']for v in old if v['input_key']==j['input_key']))for j in proof[source]if any(v['input_key']==j['input_key']for v in old)]
  else:refs=[(key,'legacy_batch')for mode in ('historical','daily')for key in proof['native'][mode]['batches']]
  targets=[]
  for key,form in refs:
   etag=s.head_object(Bucket=bucket,Key=key)['ETag'];db.enqueue(source,key,etag,form,500,c);identity=fingerprint([source,key,etag,form,policy['contract_version']]);c.execute("UPDATE engine_jobs SET priority=500 WHERE job_id=%s AND state IN ('queued','retry')",(identity,));targets.append(identity)
  out['sources'][source]={'old_jobs_superseded':len(old),'old_inputs_requeued':len(old)if source=='arxiv'else 0};out['targets'][source]=targets
 s.put_object(Bucket=bucket,Key=base+'migration.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print(source,out['sources'][source],flush=True)
print(json.dumps(out))
'''.replace('BASE',repr(BASE))
r=remote(T3,code);(P/'migration-response.json').write_text(json.dumps(r));print(r['out'])
