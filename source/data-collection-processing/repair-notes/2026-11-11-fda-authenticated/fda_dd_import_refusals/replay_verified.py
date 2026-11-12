"""Replay only the four validated Finlight jobs with normal source locks and lease fencing."""
import json,time,uuid
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.worker import process
IDS=('0ea21cdfd075537ec1d3c9eb2b55e5b9f3d57b8c4d59b0c1749e08d10e25f1bf', '9efd8287691dbaaa736a44980fed5d71fe7b75cd180ecf0f3827014344611ec0', '0bbe3754eb4ba471c21e652263966378d41455b70aa36239b500338d9d6be55f', 'e3b1265980b7c3158dbc5f1607b2d38918ded9b71baf2c666fb8cc36727cae8a', '2cb093a290f3d802f2e15c6c31774a2e8fb3e72ca4e086a5667e61cf5d88d84d', 'f30a3ba8296852bd597a28eae405906e083191c765ffb5c926b0a68caebc465e', '3a12b2efaf2a257b0f882a2783abe626120e1a8ea4744387ea1a168935b4b104', '02ddc5c277bd82c67e574f6d3982d34487822af97b03d51d39c35dbfd9e4726a', '3c150a7b4a7bee122861ad8346322263188a5c98a9f55fc36da0cded809edc90', 'a669cdeaade466d2e973ac1437beb76086ad04dfd3ffb36f20aed9574c8948b1', '41077891f97211f2afdf5dc791654f5c5e23163c081e5f3b3dbaa8b03f76d640')
config=json.loads(Path('config/metadata-engine.json').read_text());db=Database(config);s3=db.session.client('s3');started=time.monotonic()
for _ in range(len(IDS)):
 with db.tx()as c:
  c.execute("SELECT state FROM engine_sources WHERE source_key='fda_dd_import_refusals' FOR UPDATE SKIP LOCKED");source=c.fetchone()
  if not source or source['state']!='enabled':break
  c.execute("SELECT job_id FROM engine_jobs WHERE source_key='fda_dd_import_refusals' AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1")
  if c.fetchone():break
  c.execute("SELECT * FROM engine_jobs WHERE source_key='fda_dd_import_refusals' AND job_id IN %s AND state IN ('queued','retry') ORDER BY job_id LIMIT 1 FOR UPDATE",(IDS,));job=c.fetchone()
  if not job:break
  token=str(uuid.uuid4());c.execute("UPDATE engine_jobs SET state='running',lease_token=%s,lease_until=DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 600 SECOND),attempts=attempts+1 WHERE job_id=%s",(token,job['job_id']));c.execute("UPDATE engine_sources SET updated_at=UTC_TIMESTAMP(6) WHERE source_key='fda_dd_import_refusals'");job['lease_token']=token
 process(db,s3,config,job)
 if time.monotonic()-started>240:break
with db.tx()as c:
 c.execute("SELECT job_id,state,output_rows,reason FROM engine_jobs WHERE job_id IN %s",(IDS,));results=c.fetchall()
print(json.dumps({'verified_replay_results':results},default=str),flush=True)
if any(r['state']!='accepted'for r in results):raise SystemExit(2)
