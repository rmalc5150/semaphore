"""Replay only the four validated HKEX jobs with normal source locks and lease fencing."""
import json,time,uuid
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.worker import process
IDS=('46593ba8eea0a120c8c8491dd86108fca59ffb6ae750d6fe84fb1296b9e3f64d','6f092c5da838e805b5d6cd6d83d3986049fd573a13e936f0d6960de2e949b9ee','9290e6e37ae98135a9ba0e0e677d93079044ef47fe7e7231c4f99879aed5a650','eb80c4084859bd82ffd4ee27ed0d51716aea27113e8bba79212edc67d30b9112')
config=json.loads(Path('config/metadata-engine.json').read_text());db=Database(config);s3=db.session.client('s3');started=time.monotonic()
for _ in range(4):
 with db.tx()as c:
  c.execute("SELECT state FROM engine_sources WHERE source_key='hkex_news' FOR UPDATE SKIP LOCKED");source=c.fetchone()
  if not source or source['state']!='enabled':break
  c.execute("SELECT job_id FROM engine_jobs WHERE source_key='hkex_news' AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1")
  if c.fetchone():break
  c.execute("SELECT * FROM engine_jobs WHERE source_key='hkex_news' AND job_id IN %s AND state IN ('queued','retry') AND available_after<=UTC_TIMESTAMP(6) ORDER BY job_id LIMIT 1 FOR UPDATE",(IDS,));job=c.fetchone()
  if not job:break
  token=str(uuid.uuid4());c.execute("UPDATE engine_jobs SET state='running',lease_token=%s,lease_until=DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 600 SECOND),attempts=attempts+1 WHERE job_id=%s",(token,job['job_id']));c.execute("UPDATE engine_sources SET updated_at=UTC_TIMESTAMP(6) WHERE source_key='hkex_news'");job['lease_token']=token
 process(db,s3,config,job)
 if time.monotonic()-started>240:break
with db.tx()as c:
 c.execute("SELECT job_id,state,output_rows,reason FROM engine_jobs WHERE job_id IN %s",(IDS,));results=c.fetchall()
print(json.dumps({'verified_replay_results':results},default=str),flush=True)
if any(r['state']!='accepted'for r in results):raise SystemExit(2)
