"""Retry checkpointed Federal Register jobs after verified IAM repair."""
from constellation.finish_aux_migration import remote,T3

def main():
 remote(T3,'''from constellation.control import Control
from source_pauses import unit_pause,is_paused
import json,uuid
c=Control();source='legacy:constellation-specialist-federal_register.service'
routes=json.load(open('config/constellation-legacy-routes.json'))['routes'];route=next(r for r in routes if 'legacy:'+r['unit']==source)
assert route['execution_enabled'] and not unit_pause(route.get('original_unit',route['unit'])) and not is_paused('federal_register')
state=c.get('control');assert state['enabled']
with c.db()as q:
 q.execute("SELECT * FROM backfill_jobs WHERE source_key=%s AND status='blocked' AND lease_until<UNIX_TIMESTAMP()",(source,));rows=q.fetchall()
rows=[r for r in rows if json.loads(r.get('result_json')or '{}').get('checkpoint_verified') and json.loads(r['result_json']).get('exit_code')==1]
key=c.config['prefix']+'/repairs/federal-register-iam-requeue-'+uuid.uuid4().hex+'.json'
c.s3.put_object(Bucket=c.config['bucket'],Key=key,Body=json.dumps(rows,default=str).encode(),ServerSideEncryption='AES256')
changed=0
with c.db()as q:
 for i,r in enumerate(rows):
  q.execute("UPDATE backfill_jobs SET status='pending',attempts=0,lease_until=0,next_attempt_at=UNIX_TIMESTAMP()+%s,updated_at=UNIX_TIMESTAMP() WHERE job_id=%s AND status='blocked' AND lease_until<UNIX_TIMESTAMP()",(i%30,r['job_id']));changed+=q.rowcount
print(json.dumps({'requeued':changed,'failure_archive':key,'sample_job_id':rows[0]['job_id']if rows else None}))
with c.db()as q:
 q.execute("SELECT status,COUNT(*) jobs FROM backfill_jobs WHERE source_key=%s GROUP BY status",(source,));print(json.dumps({'federal_register_queue':q.fetchall()}))
''')
if __name__=='__main__':main()
