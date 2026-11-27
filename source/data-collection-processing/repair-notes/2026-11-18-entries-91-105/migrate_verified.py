from ops import *
code=r'''import json,boto3
from metadata_engine.runtime_db import Database,fingerprint
from metadata_engine.controller import register_contract
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');bucket=cfg['bucket'];base=BASE
proof=json.loads(s.get_object(Bucket=bucket,Key=base+'capture-proof.json')['Body'].read());assert proof.get('finished_at')
prepared=json.loads(s.get_object(Bucket=bucket,Key=base+'checkpoint/policies.json')['Body'].read());out={'sources':{},'targets':{},'gap_jobs':{}}
for source,policy in prepared.items():
 if source in proof['public']:assert proof['public'][source]['status']=='verified';refs=[(r['receipt_key'],'public_receipt')for r in proof['public'][source]['results']if r['status']=='verified']
 else:
  modes=proof['native'][source];assert set(modes)=={'daily','historical'}and all(e['status']=='verified'for e in modes.values());refs=[(r['key'],'legacy_batch')for e in modes.values()for r in e['batches']]
 with db.tx()as c:
  c.execute('SELECT state FROM engine_sources WHERE source_key=%s FOR UPDATE',(source,));row=c.fetchone();assert row['state']not in ('owner_paused','access_layer'),source
  c.execute("SELECT job_id FROM engine_jobs WHERE source_key=%s AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1",(source,));assert not c.fetchone(),'Active source lease; defer migration: '+source
  c.execute("SELECT * FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s AND state IN ('queued','retry','raw_failed','uncommitted') AND contract_version<>%s FOR UPDATE",(source,policy['contract_version']));old=c.fetchall();s.put_object(Bucket=bucket,Key=base+'jobs-before-'+source+'.json',Body=json.dumps(old,default=str).encode(),ServerSideEncryption='AES256')
  register_contract(db,policy,c)
  c.execute("UPDATE engine_jobs SET state='superseded',reason='legacy_input_replaced_by_verified_native_original_capture',finished_at=UTC_TIMESTAMP(6) WHERE source_key=%s AND state IN ('queued','retry','raw_failed','uncommitted') AND contract_version<>%s",(source,policy['contract_version']))
  c.execute("UPDATE engine_sources SET state='enabled',consecutive_raw_failures=0,last_reason=NULL,updated_at=UTC_TIMESTAMP(6) WHERE source_key=%s AND state='raw_stopped'",(source,))
  targets=[]
  for key,form in refs:
   etag=s.head_object(Bucket=bucket,Key=key)['ETag'];db.enqueue(source,key,etag,form,500,c);identity=fingerprint([source,key,etag,form,policy['contract_version']]);c.execute("UPDATE engine_jobs SET priority=500 WHERE job_id=%s AND state IN ('queued','retry')",(identity,));targets.append(identity)
  gaps=[]
  for e in proof['native'].get(source,{}).values():
   for failed in e['failed_batches']:
    key=failed['key'];etag=s.head_object(Bucket=bucket,Key=key)['ETag'];db.enqueue(source,key,etag,'legacy_batch',100,c);gaps.append(fingerprint([source,key,etag,'legacy_batch',policy['contract_version']]))
  out['sources'][source]={'old_inputs_superseded':len(old),'verified_batches':len(targets),'explicit_gap_batches':len(gaps)};out['targets'][source]=targets;out['gap_jobs'][source]=gaps
 print(source,out['sources'][source],flush=True)
s.put_object(Bucket=bucket,Key=base+'migration.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print('Verified contracts registered; replacement jobs queued.')
# The disabled duplicate CNINFO website route must not poison the worker queue.
from constellation.control import Control
control=Control()
with control.db()as c:
 c.execute("SELECT * FROM backfill_jobs WHERE source_key=%s AND status IN ('pending','retryable_failed') FOR UPDATE",('legacy:constellation-public-cninfo_mainland_china_company_disclosures.service',));old=c.fetchall();s.put_object(Bucket=bucket,Key=base+'cninfo-retired-route-jobs.json',Body=json.dumps(old,default=str).encode(),ServerSideEncryption='AES256')
 c.execute("UPDATE backfill_jobs SET status='blocked',result_json=%s,lease_token=NULL,lease_until=0,updated_at=UNIX_TIMESTAMP() WHERE source_key=%s AND status IN ('pending','retryable_failed')",(json.dumps({'reason':'retired_duplicate_discovery_route','replacement':'constellation-specialist-cninfo_mainland_china_company_disclosures.service','deliberately_retired':True}),'legacy:constellation-public-cninfo_mainland_china_company_disclosures.service'))
print('Disabled duplicate route retained as deliberately retired; no original data deleted.')
'''.replace('BASE',repr(BASE))
r=remote(T3,code);(P/'migration-response.json').write_text(json.dumps(r));print(r['out']);(P/'migration.json').write_bytes(session.client('s3').get_object(Bucket=B,Key=BASE+'migration.json')['Body'].read())
