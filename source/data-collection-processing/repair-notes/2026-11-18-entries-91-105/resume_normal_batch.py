from ops import *
code=r'''import json,time,fcntl,subprocess
from pathlib import Path
from constellation.control import Control
from constellation.historical_guard import dispatch_guard
from constellation.legacy_routes import manifest,specification
from source_pauses import unit_pause
sources=SOURCES;c=Control();registered=[]
with dispatch_guard(c)as acquired:
 assert acquired and c.allowed()
 for row in manifest()['routes']:
  if not row['execution_enabled']or not any(source in row['unit']for source in sources):continue
  if unit_pause(row['unit']):continue
  with c.db()as cur:
   cur.execute("SELECT job_id,status FROM backfill_jobs WHERE source_key=%s AND status IN ('pending','running','retryable_failed') AND attempts<3 LIMIT 1",('legacy:'+row['unit'],));pending=cur.fetchone()
  identity=pending['job_id']if pending else c.register(specification(row,'review-20261118-'+str(int(time.time()))))
  registered.append({'unit':row['unit'],'job_id':identity,'retained_existing':bool(pending)})
  with c.db()as cur:cur.execute("UPDATE backfill_jobs SET updated_at=0,next_attempt_at=0 WHERE job_id=%s AND status IN ('pending','retryable_failed')",(identity,))
from constellation import m7_lifecycle as life,m7_batch as batch
with (life.STATE.parent/'m7-lifecycle.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);assert life.deployment_hold_active();proof=batch.remote_control('resume');state=batch.read();state['last_checked_at']=time.time();batch.save(state)
units=['optima-public-ndb-daily','optima-public-indonesia-minerals-daily','optima-public-cfem-daily']
subprocess.run(['systemctl','enable','--now',*[u+'.timer'for u in units]],check=True);subprocess.run(['systemctl','start','--no-block',*[u+'.service'for u in units]],check=True)
out={'historical_lanes':registered,'batch_resume':proof,'daily_dispatchers_started':units,'deployment_hold':'retained until final checks'}
import boto3;boto3.client('s3',region_name='us-east-1').put_object(Bucket=BUCKET,Key=BASE+'activation.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print(json.dumps(out))
'''.replace('SOURCES',repr([s for s in SOURCES if 'kosis'not in s])).replace('BUCKET',repr(B)).replace('BASE',repr(BASE))
r=remote(T3,code);print(r['out']);(P/'activation.json').write_text(r['out'])
