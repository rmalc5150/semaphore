"""Replay only the four validated Finlight jobs with normal source locks and lease fencing."""
import json,time,uuid
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.worker import process
IDS=('2872154828d5adaadfc9506b54489817eaa386cd544315afacbae55cc816d29e', '06fd79f40a04a51f73ed62ea13b6d088f0c916da5e3d6ce4e04d236baf21f25b', 'dd65259e5e11224f5d1200d4133da58c876e80680e35f96c0d5464c5c0304e15', 'ba4b341b479a65a224c37b9e6bb8ceba0ab7ae647b7cb82c15aa79a33174ea0e', '9ee399bccd8a173d9f9d473c1a873302bc859e02e79874be1c8c4c8809f4497f', '84670be91bd05b9a5cf9c92cb6b9d645022afbee8451c2e95699133711d0877e', '9cb28d215acf281af336053bbae5fc4f51e59a3a243ed70d87fb78214d29184b', '8733005d0937547f40bd2f4db5cd82fb0575d6359eecf5326e9ade8284d86076', '971294ab5debdd452f9c46f5fb51f187f05da9d9f6a03f7ee4177ab8ebbf054e', 'c7793fc601afcdc4fe31edadf35ba2c6594dbd5dae89f64d9bf10cbb3969f93b', 'e8428c4a1f9307375c82411516844f7503c1fc9bc4b701504a6a841ff197910d')
config=json.loads(Path('config/metadata-engine.json').read_text());db=Database(config);s3=db.session.client('s3');started=time.monotonic()
for _ in range(len(IDS)):
 with db.tx()as c:
  c.execute("SELECT state FROM engine_sources WHERE source_key='europe_pmc_fulltext' FOR UPDATE SKIP LOCKED");source=c.fetchone()
  if not source or source['state']!='enabled':break
  c.execute("SELECT job_id FROM engine_jobs WHERE source_key='europe_pmc_fulltext' AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1")
  if c.fetchone():break
  c.execute("SELECT * FROM engine_jobs WHERE source_key='europe_pmc_fulltext' AND job_id IN %s AND state IN ('queued','retry') ORDER BY job_id LIMIT 1 FOR UPDATE",(IDS,));job=c.fetchone()
  if not job:break
  token=str(uuid.uuid4());c.execute("UPDATE engine_jobs SET state='running',lease_token=%s,lease_until=DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 600 SECOND),attempts=attempts+1 WHERE job_id=%s",(token,job['job_id']));c.execute("UPDATE engine_sources SET updated_at=UTC_TIMESTAMP(6) WHERE source_key='europe_pmc_fulltext'");job['lease_token']=token
 process(db,s3,config,job)
 if time.monotonic()-started>240:break
with db.tx()as c:
 c.execute("SELECT job_id,state,output_rows,reason FROM engine_jobs WHERE job_id IN %s",(IDS,));results=c.fetchall()
print(json.dumps({'verified_replay_results':results},default=str),flush=True)
if any(r['state']!='accepted'for r in results):raise SystemExit(2)
