"""Read-only preparation: copy exact partition and release restoration data."""
import json,boto3
from concurrent.futures import ThreadPoolExecutor
from metadata_engine.runtime_db import Database
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');g=db.session.client('glue');b=cfg['bucket'];base='research-data/constellation-backfill/repairs/entries-91-105-20261118/';audit=json.loads(s.get_object(Bucket=b,Key=base+'legacy-accepted-audit.json')['Body'].read());confirmed=[e for e in audit if e['classification']=='confirmed_out_of_scope_original']
def inspect(e):
 j=e['job'];partitions={}
 for table in ('source_observations','source_observations_staging'):
  try:
   p=g.get_partition(DatabaseName=cfg['athena_database'],TableName=table,PartitionValues=[j['job_id']])['Partition'];assert p['StorageDescriptor']['Location']==j['output_uri'].rsplit('/',1)[0]+'/';partitions[table]=p
  except g.exceptions.EntityNotFoundException:pass
 return {'entry':e,'partitions':partitions}
with ThreadPoolExecutor(max_workers=8)as pool:backups=list(pool.map(inspect,confirmed))
with db.tx()as c:
 release_rows=[]
 for e in confirmed:
  c.execute('SELECT HEX(release_id) release_id,release_kind,s3_uri,manifest_sha256,status,created_at,verified_at FROM publication_releases WHERE release_id=UNHEX(SUBSTRING(%s,1,32))',(e['job']['job_id'],));release_rows+=c.fetchall()
backup={'jobs_and_partitions':backups,'publication_releases':release_rows};s.put_object(Bucket=b,Key=base+'withdrawal-before.json',Body=json.dumps(backup,default=str).encode(),ServerSideEncryption='AES256')
out={'exact_jobs':len(confirmed),'published_partitions':sum('source_observations'in e['partitions']for e in backups),'staging_partitions':sum('source_observations_staging'in e['partitions']for e in backups),'backup_key':base+'withdrawal-before.json','state_changes':'none; read-only backup only'};s.put_object(Bucket=b,Key=base+'withdrawal-backup-summary.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print(json.dumps(out),flush=True)
