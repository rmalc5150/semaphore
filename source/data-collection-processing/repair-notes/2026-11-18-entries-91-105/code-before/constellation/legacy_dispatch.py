"""Controller-only historical dispatch; no collector payload runs on the t3."""
import argparse
import json
import os
import time

from constellation.control import Control
from constellation.legacy_routes import manifest, route, route_hash, specification


def dispatch(control, row):
    from constellation.historical_guard import dispatch_guard
    with dispatch_guard(control) as acquired:
        if not acquired:return {'unit':row['unit'],'status':'shutdown_check_in_progress'}
        if not control.allowed():return {'unit':row['unit'],'status':'historical_capture_paused'}
        return _dispatch(control,row)


def _dispatch(control, row):
    if os.environ.get('CONSTELLATION_ROLE','controller') != 'controller':
        raise RuntimeError('Historical dispatch belongs to the controller')
    if not row['execution_enabled']:
        return {'unit':row['unit'],'status':'staged_not_executable','requirements':row['remaining_requirements']}
    from source_pauses import unit_pause
    if unit_pause(row.get('original_unit',row['unit'])):
        return {'unit':row['unit'],'status':'operator_paused'}
    with control.db() as cursor:
        cursor.execute("SELECT /*+ MAX_EXECUTION_TIME(10000) */ spec_json,result_json FROM backfill_jobs WHERE source_key=%s AND status='succeeded' ORDER BY updated_at DESC LIMIT 1",('legacy:'+row['unit'],))
        last=cursor.fetchone()
        if last and last['result_json']:
            result=json.loads(last['result_json']);prior=json.loads(last['spec_json'])
            if result.get('route_drained') and prior['end']==row['end_exclusive'] and prior['parameters']['route_sha256']==route_hash(row):
                return {'unit':row['unit'],'status':'target_drained_with_recorded_coverage'}
        cursor.execute("SELECT /*+ MAX_EXECUTION_TIME(10000) */ job_id FROM backfill_jobs WHERE source_key=%s AND status IN ('pending','running','retryable_failed') LIMIT 1",('legacy:'+row['unit'],))
        pending = cursor.fetchone()
    if pending:
        return {'unit':row['unit'],'status':'already_queued','job_id':pending['job_id']}
    identity = control.register(specification(row,int(time.time())//row['cadence_seconds']))
    return {'unit':row['unit'],'status':'queued_on_c7i','job_id':identity,'collection_enabled':control.allowed(identity)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unit')
    parser.add_argument('--mixed-only',action='store_true')
    args=parser.parse_args()
    control=Control()
    rows=[route(args.unit)] if args.unit else [r for r in manifest()['routes'] if r['route_kind']=='split_historical']
    results=[dispatch(control,row) for row in rows]
    print(json.dumps({'execution_host':'c7i','controller_host':'t3','results':results}),flush=True)
    return 0 if all(r['status'] in {'queued_on_c7i','already_queued','operator_paused','shutdown_check_in_progress','historical_capture_paused'} for r in results) else 2


if __name__=='__main__':raise SystemExit(main())
