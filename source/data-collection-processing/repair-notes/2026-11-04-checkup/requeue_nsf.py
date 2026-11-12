import json
from pathlib import Path
from constellation.control import Control
p=Path(__file__).parent;c=Control();identity='274ddd147c83323e405c7479879a2ede4ea2989ab24db1a46976381840f917bc'
with c.db() as cursor:
 cursor.execute('SELECT * FROM backfill_jobs WHERE job_id=%s FOR UPDATE',(identity,));r=cursor.fetchone();assert r is not None
 spec=json.loads(r['spec_json']);assert spec['source_key']=='nsf_awards' and spec['start']=='2016-02-29' and spec['end']=='2016-03-01'
 (p/'nsf-job-before.json').write_text(json.dumps(r,indent=2,default=str))
 changed=False
 if r['status']=='blocked':
  cursor.execute("UPDATE backfill_jobs SET status='retryable_failed',attempts=2,next_attempt_at=0,lease_until=0,updated_at=UNIX_TIMESTAMP() WHERE job_id=%s AND status='blocked' AND lease_until<UNIX_TIMESTAMP()",(identity,));changed=cursor.rowcount==1
 print(json.dumps({'prior_status':r['status'],'one_retry_queued':changed}))
(p/'nsf-requeue.json').write_text(json.dumps({'job_id':identity,'prior_status':r['status'],'one_retry_queued':changed,'reason':'November 4 bounded probe returned 53 unique records across exhausted pagination; original result evidence preserved'},indent=2))
print('control',json.dumps(c.get('control')))
