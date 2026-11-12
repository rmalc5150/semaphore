"""Retry only journal-proven, unchanged disk-full failures; retain an audit trail."""
import json
import time
import uuid
from pathlib import Path
from constellation.control import Control,canonical
from constellation.legacy_routes import route,validate_spec
from source_pauses import is_paused,unit_pause

BASE='research-data/constellation-backfill/repairs/2026-11-12-alerts/'

def eligible(job,proof):
    if job['status'] not in {'blocked','retryable_failed'} or job['lease_until']>=time.time():return False
    result=json.loads(job['result_json'] or '{}')
    if result.get('reason')!='executor_verification_error' or result.get('error')!='OSError':return False
    if proof.get('errno')!=28 or abs(job['updated_at']-proof['at'])>5:return False
    spec=json.loads(job['spec_json'])
    try:
        validate_spec(spec)
        row=route(spec['parameters']['unit'])
    except (KeyError,ValueError):return False
    return bool(row['execution_enabled'] and not unit_pause(row['unit'])
                and not is_paused(row.get('specialist_source',row.get('public_capture_source',''))))

def main():
    c=Control();B=c.config['bucket']
    proof=json.loads(c.s3.get_object(Bucket=B,Key=BASE+'disk-full-job-evidence.json')['Body'].read())
    assert time.time()-proof['free']['checked_at']<900,'Space verification must be fresh'
    assert proof['free']['bytes']>1024**3 and proof['free']['inodes']>10000
    identities=list(proof['proof']);recovered=[];skipped=0;run_id=uuid.uuid4().hex
    for start in range(0,len(identities),20):
        before=[]
        with c.db()as cursor:
            for ident in identities[start:start+20]:
                cursor.execute('SELECT * FROM backfill_jobs WHERE job_id=%s FOR UPDATE',(ident,));job=cursor.fetchone()
                if not job or not eligible(job,proof['proof'][ident]):skipped+=1;continue
                before.append(job)
            if not before:continue
            # Preserve old states durably before changing retry eligibility.
            key=BASE+f'disk-full-requeue/{run_id}/before-{start:04d}.json'
            c.s3.put_object(Bucket=B,Key=key,Body=json.dumps(before,default=str).encode(),ServerSideEncryption='AES256',IfNoneMatch='*')
            for job in before:
                result=json.loads(job['result_json']);result['recovery']={'reason':'journal_verified_disk_full_repaired','evidence_key':BASE+'disk-full-job-evidence.json','prior_state_key':key,'at':time.time()}
                cursor.execute("UPDATE backfill_jobs SET status='pending',attempts=0,next_attempt_at=0,lease_until=0,result_json=%s,updated_at=UNIX_TIMESTAMP() WHERE job_id=%s AND status=%s AND updated_at=%s",(canonical(result).decode(),job['job_id'],job['status'],job['updated_at']))
                assert cursor.rowcount==1
                recovered.append(job['job_id'])
    receipt={'run_id':run_id,'checked_at':time.time(),'journal_proven_jobs':len(identities),'requeued':len(recovered),'requeued_job_ids':recovered,'skipped_changed_or_ineligible':skipped,'source_pauses_preserved':True}
    c.s3.put_object(Bucket=B,Key=BASE+f'disk-full-requeue/{run_id}/result.json',Body=json.dumps(receipt).encode(),ServerSideEncryption='AES256',IfNoneMatch='*')
    c.s3.put_object(Bucket=B,Key=BASE+'disk-full-requeue-result.json',Body=json.dumps(receipt).encode(),ServerSideEncryption='AES256')
    Path('constellation/migration/disk-full-requeue-result-2026-11-12.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items()if k!='requeued_job_ids'}))

if __name__=='__main__':main()
