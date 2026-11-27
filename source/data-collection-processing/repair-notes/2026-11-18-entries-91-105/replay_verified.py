import json,time,uuid
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.worker import process
from metadata_engine.controller import publish
from metadata_engine.streaming import session as streaming
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');b=cfg['bucket'];base='research-data/constellation-backfill/repairs/entries-91-105-20261118/';migration=json.loads(s.get_object(Bucket=b,Key=base+'migration.json')['Body'].read());out={'sources':{},'errors':[]};started=time.monotonic()
def save():
 out['elapsed_seconds']=round(time.monotonic()-started,2);s.put_object(Bucket=b,Key=base+'replay-publication.json',Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256')
def claim(source,identity):
 with db.tx()as c:
  c.execute('SELECT state FROM engine_sources WHERE source_key=%s FOR UPDATE',(source,));assert c.fetchone()['state']=='enabled'
  c.execute('SELECT * FROM engine_jobs WHERE job_id=%s AND source_key=%s FOR UPDATE',(identity,source));job=c.fetchone()
  if job['state']=='accepted':return None
  if job['state']not in ('queued','retry'):raise RuntimeError('Proof job not ready: '+identity+' '+job['state'])
  c.execute("SELECT job_id FROM engine_jobs WHERE source_key=%s AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1",(source,));assert not c.fetchone(),'Concurrent source lease'
  token=str(uuid.uuid4());c.execute("UPDATE engine_jobs SET state='running',lease_token=%s,lease_until=DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 20 MINUTE),attempts=attempts+1 WHERE job_id=%s",(token,identity));job['lease_token']=token;return job
for source,ids in migration['targets'].items():
 entry={'jobs':[],'publication':[]};out['sources'][source]=entry
 for identity in ids:
  try:
   job=claim(source,identity)
   if job:
    with streaming():process(db,s,cfg,job)
   with db.tx()as c:c.execute('SELECT job_id,state,output_rows,reason FROM engine_jobs WHERE job_id=%s',(identity,));entry['jobs'].append(c.fetchone())
  except Exception as e:out['errors'].append({'source':source,'job_id':identity,'error':type(e).__name__+':'+str(e)[:500]})
  save()
 for offset in range(0,len(ids),5):
  try:entry['publication'].append(publish(db,source_key=source,job_ids=ids[offset:offset+5]))
  except Exception as e:out['errors'].append({'source':source,'publication_error':type(e).__name__+':'+str(e)[:500]})
  save()
 print(source,entry,flush=True)
out['finished_at']=time.time();save();print('Verified replacements processed and bounded publication attempted.',flush=True)
