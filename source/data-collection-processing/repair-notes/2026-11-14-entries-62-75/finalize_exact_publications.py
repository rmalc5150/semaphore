import json,time
from metadata_engine.runtime_db import Database,fingerprint
from metadata_engine.reviewed_continuation import claim
from metadata_engine.worker import process
from metadata_engine.controller import publish
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');b=cfg['bucket'];base='research-data/constellation-backfill/repairs/entries-62-75-20261114/'
migration=json.loads(s.get_object(Bucket=b,Key=base+'sam-migration.json')['Body'].read());targets={'sam_gov_opportunities':[r['new']for r in migration if r['state']=='raw_failed']}
proof=json.loads(s.get_object(Bucket=b,Key=base+'copernicus-recovery.json')['Body'].read());m=json.loads(s.get_object(Bucket=b,Key='research-data/'+proof['passes'][-1]['manifest'])['Body'].read());ids=[]
for page in m['pages']:
 for batch in page['batches']:
  key='research-data/'+batch['key'];etag=s.head_object(Bucket=b,Key=key)['ETag'];ids.append(fingerprint(['copernicus_era5_era5_land',key,etag,'legacy_batch',cfg['contracts']['copernicus_era5_era5_land']['contract_version']]))
targets['copernicus_era5_era5_land']=ids;out={}
def status(ids):
 rows=[]
 with db.tx()as c:
  for identity in ids:
   c.execute('SELECT job_id,state,output_rows,reason FROM engine_jobs WHERE job_id=%s',(identity,));rows.append(c.fetchone())
 return rows
for source,ids in targets.items():
 deadline=time.monotonic()+90
 while time.monotonic()<deadline:
  rows=status(ids)
  if all(r and r['state']=='accepted'for r in rows):break
  job=claim(db,source)
  if job:process(db,s,cfg,job)
  else:time.sleep(3)
 rows=status(ids);accepted=[r['job_id']for r in rows if r and r['state']=='accepted'];published=publish(db,source_key=source,job_ids=accepted)if accepted else 0
 releases=[]
 with db.tx()as c:
  for identity in accepted:
   c.execute('SELECT status FROM publication_releases WHERE release_id=UNHEX(SUBSTRING(%s,1,32))',(identity,));releases.append({'job_id':identity,'release':c.fetchone()})
 out[source]={'jobs':rows,'published_now':published,'releases':releases};print(json.dumps(out[source]),flush=True)
s.put_object(Bucket=b,Key=base+'exact-final-publications.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');assert all(r['release']and r['release']['status']=='published'for v in out.values()for r in v['releases'])and all(j and j['state']=='accepted'for v in out.values()for j in v['jobs'])
