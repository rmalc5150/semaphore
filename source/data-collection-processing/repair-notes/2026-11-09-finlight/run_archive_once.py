"""Claim only the repaired archive retry, retaining normal fencing and executor limits."""
import uuid,signal,json,sys
sys.path.insert(0,"/opt/constellation")
from constellation.control import Control
from constellation.legacy_worker import execute,STOP
signal.signal(signal.SIGINT,lambda *_:STOP.set());signal.signal(signal.SIGTERM,lambda *_:STOP.set())
c=Control();identity='7281d035a7689b936a38478ea7d6bfe2b6b60c9c9bf6a5b9632c0368b2b07232'
assert c.allowed(identity)
with c.db()as cur:
 cur.execute("SELECT * FROM backfill_jobs WHERE job_id=%s AND status IN ('pending','retryable_failed') AND lease_until<UNIX_TIMESTAMP() AND attempts<3 FOR UPDATE",(identity,));job=cur.fetchone()
 if not job:raise SystemExit('Job already running or no longer eligible')
 token=uuid.uuid4().hex;cur.execute("UPDATE backfill_jobs SET status='running',lease_token=%s,lease_until=UNIX_TIMESTAMP()+180,worker_id='finlight-repair-20261109',updated_at=UNIX_TIMESTAMP(),attempts=attempts+1 WHERE job_id=%s",(token,identity));job.update(status='running',lease_token=token,attempts=job['attempts']+1)
execute(c,job)
