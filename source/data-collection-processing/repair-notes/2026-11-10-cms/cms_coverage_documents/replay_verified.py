"""Replay only the four validated Finlight jobs with normal source locks and lease fencing."""
import json,time,uuid
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.worker import process
IDS=('2c339a8382be770814fc16855ec1c9abd0befc975d811f256d797c169379dbcd', 'ca70b343413a318c707e8548e7ed0cfa12b72ad8aeeb00e89106de8ac768ee6e', 'f27c1ab6172cf212766b427f296cfd270b3c8a222bc7d596218033571bef4ee1', '1e372d4da635b5e19e3c6bde85092991c98274103744897c535c61f0991e3de9')
config=json.loads(Path('config/metadata-engine.json').read_text());db=Database(config);s3=db.session.client('s3');started=time.monotonic()
for _ in range(len(IDS)):
 with db.tx()as c:
  c.execute("SELECT state FROM engine_sources WHERE source_key='cms_coverage_documents' FOR UPDATE SKIP LOCKED");source=c.fetchone()
  if not source or source['state']!='enabled':break
  c.execute("SELECT job_id FROM engine_jobs WHERE source_key='cms_coverage_documents' AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1")
  if c.fetchone():break
  c.execute("SELECT * FROM engine_jobs WHERE source_key='cms_coverage_documents' AND job_id IN %s AND state IN ('queued','retry') ORDER BY job_id LIMIT 1 FOR UPDATE",(IDS,));job=c.fetchone()
  if not job:break
  token=str(uuid.uuid4());c.execute("UPDATE engine_jobs SET state='running',lease_token=%s,lease_until=DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 600 SECOND),attempts=attempts+1 WHERE job_id=%s",(token,job['job_id']));c.execute("UPDATE engine_sources SET updated_at=UTC_TIMESTAMP(6) WHERE source_key='cms_coverage_documents'");job['lease_token']=token
 process(db,s3,config,job)
 if time.monotonic()-started>240:break
with db.tx()as c:
 c.execute("SELECT job_id,state,output_rows,reason FROM engine_jobs WHERE job_id IN %s",(IDS,));results=c.fetchall()
print(json.dumps({'verified_replay_results':results},default=str),flush=True)
if any(r['state']!='accepted'for r in results):raise SystemExit(2)
