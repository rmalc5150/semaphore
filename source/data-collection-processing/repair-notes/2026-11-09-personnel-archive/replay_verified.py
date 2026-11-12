"""Replay only the four validated Finlight jobs with normal source locks and lease fencing."""
import json,time,uuid
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.worker import process
IDS=('9f8cbbb89be5d2884558d655e5bfe5c4af0bdd69a78381c7ec4c174c1c844209', 'e31d70815e5bfe2d1aecff485dd480d5ec33eee4172265fa108df4e597536016', '331f757a51090df1321512be48024408c5535bb18291c1d34f354844d72f5327', 'c0e12099a9aa51456d5b05a1e1485deaf96aaae3e6ee3763d971207d0554f35c', 'e551fcd3eab0bf46094db400ac6315352659a0d68f216e3ce661b198a6df01c2')
config=json.loads(Path('config/metadata-engine.json').read_text());db=Database(config);s3=db.session.client('s3');started=time.monotonic()
for _ in range(len(IDS)):
 with db.tx()as c:
  c.execute("SELECT state FROM engine_sources WHERE source_key='personnel_archive' FOR UPDATE SKIP LOCKED");source=c.fetchone()
  if not source or source['state']!='enabled':break
  c.execute("SELECT job_id FROM engine_jobs WHERE source_key='personnel_archive' AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1")
  if c.fetchone():break
  c.execute("SELECT * FROM engine_jobs WHERE source_key='personnel_archive' AND job_id IN %s AND state IN ('queued','retry') ORDER BY job_id LIMIT 1 FOR UPDATE",(IDS,));job=c.fetchone()
  if not job:break
  token=str(uuid.uuid4());c.execute("UPDATE engine_jobs SET state='running',lease_token=%s,lease_until=DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 600 SECOND),attempts=attempts+1 WHERE job_id=%s",(token,job['job_id']));c.execute("UPDATE engine_sources SET updated_at=UTC_TIMESTAMP(6) WHERE source_key='personnel_archive'");job['lease_token']=token
 process(db,s3,config,job)
 if time.monotonic()-started>240:break
with db.tx()as c:
 c.execute("SELECT job_id,state,output_rows,reason FROM engine_jobs WHERE job_id IN %s",(IDS,));results=c.fetchall()
print(json.dumps({'verified_replay_results':results},default=str),flush=True)
if any(r['state']!='accepted'for r in results):raise SystemExit(2)
