"""Persist honest per-source schedule/access status and maintain Athena routes.

This is a control-plane check, not a data collector. Blocked sources never become
complete merely because this job ran or an empty catalog was provisioned.
"""
import argparse
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

from collection_storage import StorageSettings, write_json
from research_contract import ROOT, load_json, digest

COLUMNS = [(n, 'string') for n in ('source_id', 'mode', 'checked_at', 'status',
    'capture_timer', 'timer_state', 'athena_database', 'api_or_url', 'priority',
    'remaining_requirement', 'historical_start_target')] + [('full_scope_complete', 'boolean')]


def validate(inventory):
    rows = inventory['sources']
    assert {r['source_id'] for r in rows} == {f'S{i:02}' for i in range(1, 69)}
    assert len(rows) == 68
    for r in rows:
        assert r['athena_database'].startswith('optima_')
        for mode in ('historical', 'daily'):
            assert r['modes'][mode]['registered']
            if not r['modes'][mode]['capture_timer']:
                assert r['modes'][mode]['status'] == 'blocked_no_capture_route'
                assert r['remaining_requirement']
    return rows


def state(timer):
    if not timer:
        return 'blocked'
    result = subprocess.run(['systemctl', 'is-enabled', timer], capture_output=True, text=True)
    return result.stdout.strip() or 'unavailable'


def check(mode, inventory, settings, store, glue):
    from botocore.exceptions import ClientError
    rows = validate(inventory)
    stamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    results = []
    timer_states = {timer: state(timer) for timer in {r['modes'][mode]['capture_timer'] for r in rows}}
    for source in rows:
        db = source['athena_database']
        # Every source has a queryable status route in its real destination DB.
        # Raw records retain their existing distinct tables/publication contracts.
        glue.get_database(Name=db)
        table = source['capture_status_table']
        location = f"s3://{settings.s3_bucket}/{settings.s3_prefix}/{source['capture_status_s3_prefix']}"
        definition = {'Name': table, 'TableType': 'EXTERNAL_TABLE',
            'Parameters': {'classification': 'json', 'optima_owner': 'source-schedule-control',
                'description': 'Capture readiness/status only; not collected source evidence'},
            'StorageDescriptor': {'Columns': [{'Name': n, 'Type': t} for n, t in COLUMNS], 'Location': location,
                'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
                'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
                'SerdeInfo': {'SerializationLibrary': 'org.openx.data.jsonserde.JsonSerDe'}}}
        try:
            old = glue.get_table(DatabaseName=db, Name=table)['Table']
            assert old.get('Parameters', {}).get('optima_owner') == 'source-schedule-control', 'Table ownership mismatch'
            assert old['StorageDescriptor']['Location'] == location, 'Table location mismatch'
        except ClientError as exc:
            if exc.response['Error']['Code'] != 'EntityNotFoundException':
                raise
            try:
                glue.create_table(DatabaseName=db, TableInput=definition)
            except ClientError as creation:
                if creation.response['Error']['Code'] != 'AlreadyExistsException':
                    raise
                concurrent = glue.get_table(DatabaseName=db, Name=table)['Table']
                assert concurrent.get('Parameters', {}).get('optima_owner') == 'source-schedule-control'
                assert concurrent['StorageDescriptor']['Location'] == location
        route = source['modes'][mode]
        timer = route['capture_timer']
        timer_state = timer_states[timer]
        status = route['status'] if timer_state in {'enabled', 'enabled-runtime', 'blocked'} else 'capture_timer_not_enabled'
        result = {'source_id': source['source_id'], 'mode': mode, 'checked_at': stamp,
            'status': status, 'capture_timer': timer or '', 'timer_state': timer_state,
            'athena_database': db, 'api_or_url': source['api_or_url'], 'priority': source['priority'],
            'remaining_requirement': source['remaining_requirement'],
            'historical_start_target': route['archive_start_target'] or '', 'full_scope_complete': False}
        # One JSON object per line for Athena; immutable receipts are elsewhere.
        body = (json.dumps(result, sort_keys=True) + '\n').encode()
        key = source['capture_status_s3_prefix'] + mode + '.json'
        prior = store.get(key)
        store.put(key, body, expected=prior.token if prior else None, content_type='application/json')
        results.append(result)
    report = {'checked_at': stamp, 'mode': mode, 'sources': results,
        'note': 'Status/control records only; running this check does not collect blocked sources.'}
    write_json(store, 'operations/source-schedule/executions/' + digest(report) + '.json', report)
    output = ROOT / 'reports/source-schedule-2026-10-09'
    output.mkdir(parents=True, exist_ok=True)
    (output / (mode + '-latest.json')).write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['daily', 'historical'], required=True)
    args = parser.parse_args()
    import boto3
    settings = StorageSettings.load(ROOT / 'config/collection-storage.s3.json')
    report = check(args.mode, load_json(ROOT / 'config/source-schedule-inventory.json'),
        settings, settings.store(), boto3.client('glue', region_name=settings.region))
    print(json.dumps({'mode': args.mode, 'sources_checked': len(report['sources']),
        'capture_routes': sum(r['status'] == 'capture_scheduled_partial_scope' for r in report['sources']),
        'blocked': sum(r['status'] == 'blocked_no_capture_route' for r in report['sources'])}))


if __name__ == '__main__':
    main()
