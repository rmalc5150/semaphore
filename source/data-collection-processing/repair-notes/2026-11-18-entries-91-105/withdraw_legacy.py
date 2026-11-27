"""Exact owner-approved withdrawal; original objects and restore backups retained."""
import json,time
from concurrent.futures import ThreadPoolExecutor
from botocore.config import Config
from metadata_engine.runtime_db import Database
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');g=db.session.client('glue',config=Config(retries={'max_attempts':12,'mode':'standard'}));b=cfg['bucket'];base='research-data/constellation-backfill/repairs/entries-91-105-20261118/';backup=json.loads(s.get_object(Bucket=b,Key=base+'withdrawal-before.json')['Body'].read());rows=backup['jobs_and_partitions'];assert len(rows)==220
from collections import Counter
assert Counter(e['entry']['job']['source_key']for e in rows)=={'china_miit_electronics_and_battery_statistics':1,'china_nea_power_statistics':1,'indonesia_esdm_and_geological_agency_mineral_statistics':117,'brazil_anm_cfem_mining_royalties':101}
for e in rows:assert e['entry']['classification']=='confirmed_out_of_scope_original'
with db.tx()as c:
 for e in rows:
  j=e['entry']['job'];c.execute("UPDATE engine_jobs SET state='superseded',reason='withdrawn_confirmed_out_of_scope_original; owner_approved_entries_91_105',finished_at=UTC_TIMESTAMP(6) WHERE job_id=%s AND source_key=%s AND state='accepted' AND contract_version=%s",(j['job_id'],j['source_key'],j['contract_version']));c.execute('SELECT state FROM engine_jobs WHERE job_id=%s',(j['job_id'],));assert c.fetchone()['state']=='superseded'
def remove(e):
 j=e['entry']['job'];removed=[]
 for table,p in e['partitions'].items():
  assert p['StorageDescriptor']['Location']==j['output_uri'].rsplit('/',1)[0]+'/'
  try:g.delete_partition(DatabaseName=cfg['athena_database'],TableName=table,PartitionValues=[j['job_id']])
  except g.exceptions.EntityNotFoundException:pass
  try:g.get_partition(DatabaseName=cfg['athena_database'],TableName=table,PartitionValues=[j['job_id']]);raise RuntimeError('Partition still exists: '+j['job_id'])
  except g.exceptions.EntityNotFoundException:removed.append(table)
 return {'job_id':j['job_id'],'source':j['source_key'],'removed_partitions':removed}
with ThreadPoolExecutor(max_workers=4)as pool:results=list(pool.map(remove,rows))
with db.tx()as c:
 for e in rows:c.execute("UPDATE publication_releases SET status='failed' WHERE release_id=UNHEX(SUBSTRING(%s,1,32))",(e['entry']['job']['job_id'],))
out={'withdrawn_jobs':len(rows),'published_partitions_removed':sum('source_observations'in e['removed_partitions']for e in results),'results':results,'original_objects':'retained','approval':'explicit owner approval received 18 November 2026','checked_at':time.time()};s.put_object(Bucket=b,Key=base+'withdrawal-verified.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print(json.dumps({k:v for k,v in out.items()if k!='results'}),flush=True)
