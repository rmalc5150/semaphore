"""Execute one reviewed migration probe, then restore the paused queue state."""
from datetime import datetime, timezone
import json
import argparse
from pathlib import Path
import time

from constellation.control import Control
from constellation.legacy_routes import route,specification


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag',default='migration-v1')
    args=parser.parse_args()
    control=Control();state=control.get('control')
    if state['enabled'] or state['pilot_job_ids']:raise RuntimeError('Pause collection before a migration pilot')
    row=route('constellation-core-migration-probe.service')
    identity=control.register(specification(row,str(int(time.time())//row['cadence_seconds'])+':'+args.tag))
    initial=control.get('job#'+identity)
    if initial['status']=='retryable_failed':
        with control.db() as cursor:
            cursor.execute("UPDATE backfill_jobs SET next_attempt_at=0 WHERE job_id=%s AND status='retryable_failed'",(identity,))
    baseline_attempts=initial['attempts']
    results={}
    try:
        control.set_enabled(False,[identity])
        last=None;deadline=time.monotonic()+420
        while time.monotonic()<deadline:
            job=control.get('job#'+identity)
            if job['status']!=last:print(json.dumps({'migration_probe':job['status']}),flush=True);last=job['status']
            if job['status']=='succeeded' or (job['status'] in {'retryable_failed','blocked'} and job['attempts']>baseline_attempts):
                results={'job_id':identity,'worker_id':job['worker_id'],'status':job['status'],
                    'result':json.loads(job['result_json']), 'checked_at':datetime.now(timezone.utc).isoformat()}
                Path(__file__).with_name('migration').joinpath('pilot-latest.json').write_text(json.dumps(results,indent=2)+'\n')
                print(json.dumps(results),flush=True)
                if job['status']!='succeeded':raise RuntimeError('Migration probe incomplete; inspect its S3 report')
                return
            time.sleep(3)
        raise RuntimeError('Migration probe deadline exceeded')
    finally:control.set_enabled(False,[])


if __name__=='__main__':main()
