"""Live operational-queue checks; no provider calls or application-table writes.

A clearly labeled synthetic row is retained as blocked audit evidence. Existing
pause/pilot state is restored, and a test refuses to run while backfill is enabled.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
import uuid

import pymysql

from constellation.control import Control, LeaseLost


def main():
    control = Control()
    state = control.get('control')
    if state['enabled'] or state['pilot_job_ids']:
        raise RuntimeError('Run only while collection is fully paused')
    identity = uuid.uuid4().hex + uuid.uuid4().hex
    with control.db() as cursor:
        cursor.execute("INSERT INTO backfill_jobs(job_id,source_key,spec_json,status,created_at,updated_at) VALUES(%s,'__lease_check__',%s,'pending',UNIX_TIMESTAMP(),UNIX_TIMESTAMP())",
            (identity, '{"synthetic":true}'))
    checks = []
    try:
        control.set_enabled(False, [identity])
        with ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(lambda worker: Control().claim_next(worker), ['lease-check-a', 'lease-check-b']))
        winners = [row for row in rows if row]
        if len(winners) != 1:
            raise AssertionError('Concurrent claims produced ' + str(len(winners)) + ' owners')
        checks.append('exactly_one_concurrent_lease')
        first = winners[0]['lease_token']
        with control.db() as cursor:
            cursor.execute('UPDATE backfill_jobs SET lease_until=UNIX_TIMESTAMP()-1 WHERE job_id=%s', (identity,))
        second = control.claim_next('lease-check-recovery')
        if not second or second['lease_token'] == first:
            raise AssertionError('Expired lease did not recover with a new token')
        checks.append('expired_lease_recovered')
        try:
            control.finish(identity, first, 'blocked', {'reason': 'stale test owner'})
        except LeaseLost:
            checks.append('stale_owner_cannot_commit')
        else:
            raise AssertionError('Stale lease committed')
        control.finish(identity, second['lease_token'], 'blocked', {'reason': 'synthetic_lease_check_no_provider_calls', 'coverage_status': 'not_yet_audited'})
        os.environ['CONSTELLATION_ROLE'] = 'worker'
        worker = Control()
        del os.environ['CONSTELLATION_ROLE']
        for label, sql in [
                ('worker_cannot_enable_collection', 'UPDATE backfill_control SET enabled=1 WHERE singleton=1'),
                ('worker_cannot_change_partition_spec', "UPDATE backfill_jobs SET spec_json='{}' WHERE job_id='" + identity + "'"),
                ('worker_cannot_read_metadata_application_data', 'SELECT entity_id FROM metadata_engine.entities LIMIT 1')]:
            try:
                with worker.db() as cursor:
                    cursor.execute(sql)
            except pymysql.err.OperationalError as exc:
                if exc.args[0] not in {1142, 1143}:
                    raise
                checks.append(label)
            else:
                raise AssertionError(label + ' unexpectedly allowed')
        print(json.dumps({'status': 'passed', 'checks': checks, 'synthetic_job_id': identity}))
    finally:
        control.set_enabled(False, [])
        with control.db() as cursor:
            cursor.execute("UPDATE backfill_jobs SET status='blocked',lease_until=0,result_json=%s WHERE job_id=%s",
                (json.dumps({'reason': 'synthetic_lease_check_no_provider_calls', 'coverage_status': 'not_yet_audited'}), identity))


if __name__ == '__main__':
    main()
