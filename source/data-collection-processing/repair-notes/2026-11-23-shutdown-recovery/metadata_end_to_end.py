import os,sys,json,fcntl,time
from pathlib import Path
root=Path('/opt/constellation/metadata-engine-runtime');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
from metadata_engine.runtime_db import Database
from metadata_engine.controller import publish
cfg=json.loads((root/'config/metadata-engine.json').read_text());db=Database(cfg)
with db.tx()as c:
 c.execute("SELECT job_id,source_key,output_rows,output_uri FROM engine_jobs FORCE INDEX (publication_ready_order) WHERE state='accepted' ORDER BY finished_at DESC,job_id DESC LIMIT 1");job=c.fetchone()
print('TARGET',json.dumps(job),flush=True)
with Path('/opt/constellation/auxiliary-publication/publish.lock').open('a')as lock:
 deadline=time.monotonic()+120
 while True:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
  except BlockingIOError:
   if time.monotonic()>deadline:print('WAITING_FOR_PUBLISHER_LOCK',flush=True);raise SystemExit(0)
   time.sleep(2)
 print('PUBLISHED',publish(db,source_key=job['source_key'],job_ids=[job['job_id']]),flush=True)
