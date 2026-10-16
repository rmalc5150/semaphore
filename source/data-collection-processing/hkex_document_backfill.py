#!/usr/bin/env python3
"""Bounded, resumable HKEX original-document backfill with verified completion email."""
from datetime import date, timedelta
import argparse
import fcntl
import json

import disclosure_collection as disclosure
from collection_storage import StorageSettings, now, write_json
from research_contract import ROOT, digest, load_json
from regulatory_collection import require


def read(store, key):
    obj = store.get(key)
    return json.loads(obj.body) if obj else None


def save(store, key, value):
    previous = store.get(key)
    write_json(store, key, value, previous.token if previous else None)


def identity(config, universe, taxonomy):
    return digest({"version": "hkex-document-backfill-1", "collector": disclosure.VERSION,
        "config": config, "universe": digest(universe), "taxonomy": digest(taxonomy)})


def verify_day(store, result, universe, taxonomy, day):
    entries, _, manifests = disclosure.read_inputs(store, [result['manifest']], universe, taxonomy)
    manifest = manifests[0]
    task = manifest['task']
    require(task['source'] == 'hkex_news' and task['dataset'] == 'filings', 'wrong_backfill_source')
    require(task['scope']['selection'] == 'all' and task['scope']['stock_id'] == '' and
            task['scope']['document_capture'] == 'original_bytes_v1', 'wrong_backfill_scope')
    disclosure.check_coverage(manifests, day, day + timedelta(days=1), ['hkex_news'])
    total_bytes = 0
    for entry in entries:
        record = entry['record']
        capture = record['payload'].get('document_capture', {})
        require(capture.get('status') == 'captured', 'backfill_document_missing')
        refs = capture.get('source_evidence', [])
        require(len(refs) == 1 and refs[0]['source_url'] == record['source_url'], 'backfill_document_reference_invalid')
        require(refs[0] in record['payload']['source_evidence'], 'backfill_document_evidence_missing')
        raw = disclosure.get_bytes(store, refs[0]['key'], refs[0]['sha256'])
        require(len(raw) == capture['bytes'] and len(raw) > 0, 'backfill_document_size_mismatch')
        total_bytes += len(raw)
    return {'date': str(day), 'manifest': result['manifest'], 'manifest_sha256': digest(manifest),
            'records': len(entries), 'document_bytes': total_bytes, 'verified_at': now()}


def run(store, settings, config, universe, taxonomy, sns, collector=disclosure.collect_hkex):
    start, end = date.fromisoformat(config['start']), date.fromisoformat(config['end_exclusive'])
    require(start < end <= date.today(), 'invalid_backfill_window')
    require(config['selection'] == 'all', 'backfill_requires_all_announcements')
    prefix = 'operations/hkex-document-backfill/' + identity(config, universe, taxonomy)
    state_key = prefix + '/state.json'
    state = read(store, state_key) or {'next_date': str(start), 'status': 'running', 'started_at': now()}
    cursor = date.fromisoformat(state['next_date'])
    require(start <= cursor <= end, 'invalid_backfill_cursor')
    if state.get('notification_message_id'):
        return state
    for _ in range(config['max_days_per_invocation']):
        if cursor >= end:
            break
        result = collector(store, settings, universe, taxonomy, cursor, cursor + timedelta(days=1),
            'historical', selection='all', page_size=config['page_size'],
            max_pages=config['max_pages_per_day_per_invocation'], capture_documents=True)
        if result['status'] != 'complete':
            state.update(status=result['status'], last_result=result, updated_at=now())
            save(store, state_key, state)
            return {**state, 'state_key': state_key}
        receipt = verify_day(store, result, universe, taxonomy, cursor)
        save(store, prefix + '/days/' + str(cursor) + '.json', receipt)
        cursor += timedelta(days=1)
        state.update(next_date=str(cursor), status='running', updated_at=now(), last_result=result)
        save(store, state_key, state)
        print(json.dumps({'stage': 'verified_day', **receipt}), flush=True)
    if cursor < end:
        return {**state, 'state_key': state_key}
    # Require every daily receipt and its immutable committed manifest before notifying.
    cursor, count, total_bytes, receipts = start, 0, 0, []
    while cursor < end:
        receipt = read(store, prefix + '/days/' + str(cursor) + '.json')
        require(receipt is not None and receipt['date'] == str(cursor), 'backfill_receipt_missing')
        manifest = read(store, receipt['manifest'])
        require(manifest is not None and digest(manifest) == receipt['manifest_sha256'], 'backfill_manifest_changed')
        require(manifest['status'] == 'complete' and manifest['exhausted'] and
                manifest['record_count'] == receipt['records'], 'backfill_manifest_incomplete')
        head = read(store, 'checkpoints/' + manifest['task_id'] + '/head.json')
        require(head is not None and receipt['manifest'] in head['terminal_history'], 'backfill_manifest_uncommitted')
        count += receipt['records']
        total_bytes += receipt['document_bytes']
        receipts.append(receipt)
        cursor += timedelta(days=1)
    summary = {'start': str(start), 'end_exclusive': str(end), 'days_verified': len(receipts),
        'reports_captured': count, 'document_bytes': total_bytes, 'receipts_sha256': digest(receipts),
        'scope_note': config['scope_note'], 'verified_at': now()}
    summary_key = prefix + '/completion.json'
    save(store, summary_key, summary)
    # Verify the existing topic still targets only the requested recipient.
    subscriptions = []
    for page in sns.get_paginator('list_subscriptions_by_topic').paginate(TopicArn=config['email_topic_arn']):
        subscriptions.extend(page['Subscriptions'])
    require(bool(subscriptions) and all(s['Protocol'] == 'email' and
        s['Endpoint'] == config['email_recipient'] and s['SubscriptionArn'].startswith('arn:')
        for s in subscriptions), 'completion_email_subscription_mismatch')
    message = sns.publish(TopicArn=config['email_topic_arn'], Subject='HKEX report backfill complete — verified original documents',
        Message=(f"HKEX report backfill completed and verified.\n\n"
            f"Range: {start} through {end - timedelta(days=1)} (inclusive).\n"
            f"Days verified: {len(receipts)}\nReports captured: {count}\nOriginal document bytes: {total_bytes}\n\n"
            f"{config['scope_note']}\n\nCompletion receipt: {summary_key}\n"))
    # SNS acceptance followed by a failed state write may cause a duplicate notification on retry.
    state.update(status='complete', completed_at=now(), completion_key=summary_key,
                 notification_message_id=message['MessageId'], reports_captured=count)
    save(store, state_key, state)
    return {**state, 'state_key': state_key}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='config/hkex-document-backfill.json')
    args = parser.parse_args()
    config = load_json(ROOT / args.config)
    with (ROOT / '.hkex-document-backfill.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({'status': 'partial', 'reason': 'already_running'}))
            return 2
        import boto3
        settings = StorageSettings.load(ROOT / config['storage_config'])
        result = run(settings.store(), settings, config, load_json(ROOT / config['universe']),
            load_json(ROOT / config['taxonomy']), boto3.client('sns', region_name=settings.region))
        print(json.dumps(result), flush=True)
        return 0 if result['status'] == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
