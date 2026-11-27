"""Controller-only historical dispatch; no collector payload runs on the t3."""
import argparse
import json
import os
from pathlib import Path
import time

from constellation.control import Control
from constellation.legacy_routes import manifest, route, route_hash, specification
from constellation.trial_historical_access import INSTANCE as TRIAL_INSTANCE, OPENDART, owns_opendart

TRIAL_TRANSFER = Path(__file__).resolve().parents[1] / 'constellation/autostop/trial-specialist-transfer.json'
TRIAL_SOURCES = frozenset({'imf_portwatch_shipping_activity','copernicus_era5_era5_land'})
OPENDART_SCOPE_UPDATE = TRIAL_TRANSFER.with_name('opendart-scope-update.json')
OPENDART_OWNER = TRIAL_TRANSFER.with_name('opendart-owner.json')


def _trial_opendart(row):
    if row.get('specialist_source') == OPENDART and owns_opendart(OPENDART_OWNER):
        return {'unit': row['unit'], 'status': 'delegated_to_trial', 'instance_id': TRIAL_INSTANCE}
    return None


def dispatch(control, row):
    delegated = _trial_opendart(row)
    if delegated: return delegated
    from constellation.historical_guard import dispatch_guard
    with dispatch_guard(control) as acquired:
        if not acquired:return {'unit':row['unit'],'status':'shutdown_check_in_progress'}
        if not control.allowed():return {'unit':row['unit'],'status':'historical_capture_paused'}
        return _dispatch(control,row)


def _dispatch(control, row):
    if os.environ.get('CONSTELLATION_ROLE','controller') != 'controller':
        raise RuntimeError('Historical dispatch belongs to the controller')
    delegated = _trial_opendart(row)
    if delegated: return delegated
    if not row['execution_enabled']:
        return {'unit':row['unit'],'status':'staged_not_executable','requirements':row['remaining_requirements']}
    if row.get('specialist_source') in TRIAL_SOURCES and TRIAL_TRANSFER.is_file():
        return {'unit':row['unit'],'status':'delegated_to_trial','instance_id':'i-08311762628a9830f'}
    if row.get('specialist_source')=='south_korea_fss_opendart' and OPENDART_SCOPE_UPDATE.is_file():
        return {'unit':row['unit'],'status':'opendart_scope_update'}
    from source_pauses import unit_pause
    if unit_pause(row.get('original_unit',row['unit'])):
        return {'unit':row['unit'],'status':'operator_paused'}
    with control.db() as cursor:
        cursor.execute("SELECT /*+ MAX_EXECUTION_TIME(10000) */ spec_json,result_json FROM backfill_jobs WHERE source_key=%s AND status='succeeded' ORDER BY updated_at DESC LIMIT 1",('legacy:'+row['unit'],))
        last=cursor.fetchone()
        if last and last['result_json']:
            result=json.loads(last['result_json']);prior=json.loads(last['spec_json'])
            if row.get('route_kind')!='independent_public_daily' and result.get('route_drained') and prior['end']==row['end_exclusive'] and prior['parameters']['route_sha256']==route_hash(row):
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
    return 0 if all(r['status'] in {'queued_on_c7i','already_queued','operator_paused','shutdown_check_in_progress','historical_capture_paused','delegated_to_trial','opendart_scope_update'} for r in results) else 2


if __name__=='__main__':raise SystemExit(main())
