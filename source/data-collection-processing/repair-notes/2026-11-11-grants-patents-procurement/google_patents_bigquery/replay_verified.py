"""Replay only the four validated HKEX jobs with normal source locks and lease fencing."""
import json,time,uuid
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.worker import process
IDS=('788cf79a0e94bfad1fdd1c97f3943ceca1be6961ea9c1a780e525ade9170dd32', '39836044bf02124181c8bd83df6495885fe3b2f1e9c66a51ca6345a502d54c4d', 'efe69d77d63f309b78dfa6d3e9c957039aeffda9a5538ac917b955765aef407a', '29bd04f7ec8aad557f1844ff5ef4be72c6ef76252bfb979736416ceee3950434')
config=json.loads(Path('config/metadata-engine.json').read_text());db=Database(config);s3=db.session.client('s3');started=time.monotonic()
for _ in range(len(IDS)):
 with db.tx()as c:
  c.execute("SELECT state FROM engine_sources WHERE source_key='google_patents_bigquery' FOR UPDATE SKIP LOCKED");source=c.fetchone()
  if not source or source['state']!='enabled':break
  c.execute("SELECT job_id FROM engine_jobs WHERE source_key='google_patents_bigquery' AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1")
  if c.fetchone():break
  c.execute("SELECT * FROM engine_jobs WHERE source_key='google_patents_bigquery' AND job_id IN %s AND state IN ('queued','retry') ORDER BY job_id LIMIT 1 FOR UPDATE",(IDS,));job=c.fetchone()
  if not job:break
  token=str(uuid.uuid4());c.execute("UPDATE engine_jobs SET state='running',lease_token=%s,lease_until=DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 600 SECOND),attempts=attempts+1 WHERE job_id=%s",(token,job['job_id']));c.execute("UPDATE engine_sources SET updated_at=UTC_TIMESTAMP(6) WHERE source_key='google_patents_bigquery'");job['lease_token']=token
 process(db,s3,config,job)
 if time.monotonic()-started>240:break
with db.tx()as c:
 c.execute("SELECT job_id,state,output_rows,reason FROM engine_jobs WHERE job_id IN %s",(IDS,));results=c.fetchall()
print(json.dumps({'verified_replay_results':results},default=str),flush=True)
if any(r['state']!='accepted'for r in results):raise SystemExit(2)
