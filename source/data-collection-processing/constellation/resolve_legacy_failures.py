"""Close superseded invocation failures while retaining their original evidence."""
import argparse
from collections import Counter
import hashlib
import json
import uuid

from constellation.control import Control, canonical
from constellation.legacy_routes import route, validate_spec
from constellation.legacy_worker import checkpoint_events
from constellation.worker import put_verified
from source_pauses import unit_pause


def invocation_scope(row):
    spec = json.loads(row['spec_json'])
    spec['parameters'].pop('dispatch_slot')
    return spec


def read_evidence(control, key, limit):
    with control.s3.get_object(Bucket=control.config['bucket'], Key=key)['Body'] as body:
        data = body.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Historical evidence exceeds size limit: ' + key)
    return data


def replacement_proof(control, replacement, unit):
    result = json.loads(replacement['result_json'] or '{}')
    prefix = control.config['prefix']
    bucket = 's3://' + control.config['bucket'] + '/'
    reports = bucket + prefix + '/legacy-reports/' + replacement['job_id'] + '/'
    report_uri = result.get('report_uri', '')
    if result.get('checkpoint_verified') is not True or not report_uri.startswith(reports):
        return None
    events = checkpoint_events(read_evidence(control, report_uri.removeprefix(bucket), 16 * 1024 ** 2), unit)
    if not events:
        return None
    run = events[-1]['run_id']
    key = f'{prefix}/legacy-runtime/{unit}/manifests/{run}.json'
    data = read_evidence(control, key, 64 * 1024 ** 2)
    manifest = json.loads(data)
    if manifest.get('unit') != unit or manifest.get('run_id') != run:
        return None
    return {'status': 'superseded', 'replacement_job_id': replacement['job_id'],
            'replacement_report_uri': report_uri, 'checkpoint_manifest_uri': bucket + key,
            'checkpoint_manifest_sha256': hashlib.sha256(data).hexdigest(),
            'replacement_route_drained': result.get('route_drained') is True}


def candidates(control):
    proposed = []
    with control.db() as cursor:
        cursor.execute("SELECT * FROM backfill_jobs FORCE INDEX (claimable) WHERE status='blocked' AND source_key LIKE 'legacy:%'")
        by_source = {}
        for row in cursor.fetchall():
            if json.loads(row['result_json'] or '{}').get('resolution', {}).get('status') != 'superseded':
                by_source.setdefault(row['source_key'], []).append(row)
        for source, rows in by_source.items():
            unit = source.removeprefix('legacy:')
            route_spec = route(unit)
            if not route_spec['execution_enabled'] or unit_pause(route_spec.get('original_unit', unit)):
                continue
            cursor.execute("SELECT * FROM backfill_jobs FORCE INDEX (source_status_updated) WHERE source_key=%s AND status='succeeded' ORDER BY updated_at DESC LIMIT 1", (source,))
            replacement = cursor.fetchone()
            if not replacement:
                continue
            validate_spec(json.loads(replacement['spec_json']))
            cursor.execute("SELECT spec_json FROM backfill_jobs FORCE INDEX (source_status_updated) WHERE source_key=%s AND status IN ('pending','retryable_failed','running') AND attempts<3", (source,))
            live_scope = any(invocation_scope(row) == invocation_scope(replacement) for row in cursor.fetchall())
            for row in rows:
                prior = json.loads(row['result_json'] or '{}')
                diagnostic = (route_spec['route_kind'] == 'migration_probe'
                              and prior.get('reason') == 'superseded_executor_diagnostic'
                              and prior.get('superseded_by_job_id') == replacement['job_id'])
                same_scope = row['updated_at'] < replacement['updated_at'] and invocation_scope(row) == invocation_scope(replacement)
                if diagnostic or same_scope:
                    proposed.append((row, replacement, unit, diagnostic or live_scope))
    proofs = {}
    for row, replacement, unit, live_or_diagnostic in proposed:
        identity = replacement['job_id']
        if identity not in proofs:
            proofs[identity] = replacement_proof(control, replacement, unit)
        proof = proofs[identity]
        if proof and (live_or_diagnostic or proof['replacement_route_drained']):
            yield row, proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    control = Control()
    selected = list(candidates(control))
    receipt = {'proposed': len(selected), 'by_route': Counter(row['source_key'] for row, _ in selected)}
    if args.apply and selected:
        key = control.config['prefix'] + '/repairs/legacy-invocations-' + uuid.uuid4().hex + '.json'
        archive = put_verified(control, key, canonical(selected), 'application/json')['uri']
        with control.db() as cursor:
            for row, proof in selected:
                cursor.execute('SELECT status,result_json FROM backfill_jobs WHERE job_id=%s FOR UPDATE', (row['job_id'],))
                current = cursor.fetchone()
                if current != {'status': 'blocked', 'result_json': row['result_json']}:
                    raise RuntimeError('Historical job changed during verification: ' + row['job_id'])
                result = json.loads(row['result_json'] or '{}')
                result['resolution'] = {**proof, 'prior_failure_archive': archive}
                cursor.execute('UPDATE backfill_jobs SET result_json=%s WHERE job_id=%s',
                               (canonical(result).decode(), row['job_id']))
        receipt.update(resolved=len(selected), archive=archive)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
