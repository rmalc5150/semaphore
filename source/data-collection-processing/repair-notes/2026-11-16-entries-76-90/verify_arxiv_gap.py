import sys,json,hashlib
sys.path.insert(0,'/opt/constellation/metadata-engine-runtime')
from metadata_engine.runtime_db import Database,collection_tx,fingerprint
from metadata_engine.worker import load_input
from metadata_engine.evidence import evidence_for,object_bytes
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');b=cfg['bucket'];base='research-data/constellation-backfill/repairs/entries-76-90-20261116/';repair=json.loads(s.get_object(Bucket=b,Key=base+'arxiv-gap-repair.json')['Body'].read());old=json.loads(s.get_object(Bucket=b,Key=base+'arxiv-uncommitted.json')['Body'].read())
with collection_tx(db.session,cfg)as c:c.execute('SELECT status,result_json FROM backfill_jobs WHERE job_id=%s',(repair['job_id'],));job=c.fetchone()
assert job['status']=='succeeded';result=json.loads(job['result_json']);key=result['manifest_uri'].split(b+'/',1)[1];mraw=object_bytes(s,b,key,expected=result['manifest_sha256']);manifest=json.loads(mraw);assert manifest['pagination_exhausted'];verified=0
for page in range(len(manifest['pages'])):
 rows,_,_=load_input(s,b,{'input_key':key,'input_format':'native_manifest:'+str(page)},db)
 for row in rows:evidence_for(row,cfg['contracts']['arxiv'],s,b);verified+=1
assert verified==result['records']==1647
etag=s.head_object(Bucket=b,Key=key)['ETag'];db.enqueue('arxiv',key,etag,'native_manifest',550);new=fingerprint(['arxiv',key,etag,'native_manifest',cfg['contracts']['arxiv']['contract_version']]);retired=[]
with db.tx()as c:
 c.execute("SELECT * FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key='arxiv' AND state='uncommitted'");candidates=c.fetchall()
 for candidate in candidates:
  if candidate['input_key']!=old['key']:continue
  s.put_object(Bucket=b,Key=base+'arxiv-old-uncommitted-job.json',Body=json.dumps(candidate,default=str).encode(),ServerSideEncryption='AES256')
  c.execute("UPDATE engine_jobs SET state='superseded',reason=%s,finished_at=UTC_TIMESTAMP(6) WHERE job_id=%s AND state='uncommitted'",('incomplete_daily_snapshot_replaced_by_committed_native:'+repair['job_id'],candidate['job_id']));retired.append(candidate['job_id'])
 c.execute("UPDATE engine_jobs SET priority=550 WHERE job_id=%s AND state IN ('queued','retry')",(new,))
out={'status':'verified','records':verified,'manifest_uri':result['manifest_uri'],'manifest_sha256':result['manifest_sha256'],'new_metadata_job_id':new,'superseded_incomplete_jobs':retired,'scope':'Complete replacement API query for 2026-10-27; citation/abstract data only, not full text or original historical vintages.'};s.put_object(Bucket=b,Key=base+'arxiv-gap-verified.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print(json.dumps(out),flush=True)
