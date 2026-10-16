#!/usr/bin/env python3
"""Resumable EDINET report/extraction backfill; email only after verified inventory exhaustion."""
import argparse
from datetime import date, timedelta
import fcntl
import hashlib
import json

import edinet_pipeline as pipeline
from collection_storage import StorageSettings, now, write_json
from research_contract import ROOT, digest, load_json, validate_record
from regulatory_collection import require


def read(store, key):
    obj = store.get(key)
    return json.loads(obj.body) if obj else None


def save(store, key, value):
    obj = store.get(key)
    write_json(store, key, value, obj.token if obj else None)


def job(day):
    return {'source_id': 'S10', 'source': 'edinet_filings', 'adapter': 'edinet', 'mode': 'historical',
        'start': str(day), 'end': str(day + timedelta(days=1)),
        'parameters': {'url': pipeline.API + '/documents.json', 'date': str(day), 'pipeline_version': pipeline.VERSION},
        'coverage_note': pipeline.COVERAGE}


def verified_bytes(store, ref):
    obj = store.get(ref['key'])
    require(obj is not None and hashlib.sha256(obj.body).hexdigest() == ref['sha256'], 'edinet_evidence_checksum_mismatch')
    return obj.body


def verify_day(store, manifest_key, universe, taxonomy, day):
    manifest = read(store, manifest_key)
    require(manifest is not None and manifest['status'] == 'complete' and manifest['exhausted'], 'edinet_manifest_incomplete')
    task = manifest['task']
    require(task['source'] == 'edinet_filings' and task['dataset'] == 'specialist_inputs' and
        task['collector_version'] == pipeline.VERSION and task['scope']['parameters']['date'] == str(day) and
        task['universe_hash'] == digest(universe) and task['taxonomy_hash'] == digest(taxonomy), 'edinet_manifest_scope_mismatch')
    require(manifest['task_id'] == 'task_' + digest(task), 'edinet_manifest_identity_mismatch')
    head = read(store, 'checkpoints/' + manifest['task_id'] + '/head.json')
    require(head is not None and head['task'] == task and manifest_key in head['terminal_history'], 'edinet_manifest_uncommitted')
    counts = {'records': 0, 'reports_captured': 0, 'original_files': 0, 'source_gaps': 0,
        'no_text_reports': 0, 'textless_pdf_pages': 0, 'verified_company_matches': 0, 'candidate_matches': 0, 'unresolved_matches': 0}
    seen = set()
    for page in manifest['pages']:
        page_count = 0
        for batch in page['batches']:
            raw = verified_bytes(store, batch)
            require(len(raw) == batch['bytes'], 'edinet_batch_size_mismatch')
            rows = [json.loads(line) for line in raw.splitlines()]
            require(len(rows) == batch['records'], 'edinet_batch_count_mismatch')
            for record in rows:
                require(not validate_record(record, universe), 'edinet_record_invalid')
                require(record['source'] == 'edinet_filings' and record['run_id'] == page['run_id'] and
                    record['observation_id'] not in seen, 'edinet_record_scope_or_duplicate')
                seen.add(record['observation_id'])
                payload = record['payload']
                require(payload['pipeline_version'] == pipeline.VERSION and payload['entity_link_status'] in
                    ('matched', 'candidate', 'unresolved'), 'edinet_processing_missing')
                evidence = {(r['key'], r['sha256']) for r in payload['source_evidence']}
                docs = payload['documents']
                expected = {kind for kind, flag, _ in pipeline.FORMATS if payload['data'].get(flag) == '1'}
                captured = payload['document_capture_status'] == 'captured'
                if captured:
                    require({d['type'] for d in docs} == expected, 'edinet_advertised_document_missing')
                else:
                    require(not docs and payload['document_capture_status'] in
                        ('source_unavailable', 'no_advertised_documents'), 'edinet_document_capture_invalid')
                for ref in payload['source_evidence']:
                    verified_bytes(store, ref)
                for document in docs:
                    require(len(document['source_evidence']) == 1, 'edinet_original_reference_missing')
                    ref = document['source_evidence'][0]
                    require((ref['key'], ref['sha256']) in evidence and
                        len(verified_bytes(store, ref)) == document['bytes'], 'edinet_original_evidence_mismatch')
                    refs = document['extraction']['source_evidence']
                    require(len(refs) == 1 and (refs[0]['key'], refs[0]['sha256']) in evidence,
                        'edinet_extraction_reference_missing')
                    extracted = json.loads(verified_bytes(store, refs[0]))
                    require(extracted['version'] == pipeline.VERSION and extracted['text_characters'] ==
                        document['extraction']['text_characters'], 'edinet_extraction_mismatch')
                counts['records'] += 1
                counts['reports_captured'] += int(captured)
                counts['original_files'] += len(docs)
                counts['source_gaps'] += int(not captured)
                counts['no_text_reports'] += int(captured and payload['content_extraction_status'] != 'extracted')
                counts['textless_pdf_pages'] += payload['textless_pdf_pages']
                counts[{'matched': 'verified_company_matches', 'candidate': 'candidate_matches',
                    'unresolved': 'unresolved_matches'}[payload['entity_link_status']]] += 1
            page_count += len(rows)
        require(page_count == page['record_count'], 'edinet_page_count_mismatch')
    require(counts['records'] == manifest['record_count'] == manifest['expected_records'], 'edinet_manifest_count_mismatch')
    return {'date': str(day), 'manifest': manifest_key, 'manifest_sha256': digest(manifest), 'verified_at': now(), **counts}


def run(store, settings, config, universe, taxonomy, sns, collector=pipeline.collect):
    start, end = date.fromisoformat(config['start']), date.fromisoformat(config['end_exclusive'])
    require(start < end <= date.today(), 'edinet_backfill_window_invalid')
    identity = digest({'config': config, 'pipeline': pipeline.VERSION, 'universe': digest(universe), 'taxonomy': digest(taxonomy)})
    prefix = 'operations/edinet-document-backfill/' + identity
    state_key = prefix + '/state.json'
    state = read(store, state_key) or {'next_date': str(start), 'status': 'running', 'started_at': now()}
    if state.get('notification_message_id'):
        return state
    day = date.fromisoformat(state['next_date'])
    require(start <= day <= end, 'edinet_backfill_cursor_invalid')
    for _ in range(config['max_days_per_invocation']):
        if day >= end:
            break
        scope = job(day)
        result = collector(scope, store, settings, universe, taxonomy, config['documents_per_invocation'])
        if result['status'] != 'complete':
            state.update(status=result['status'], last_result=result, updated_at=now())
            save(store, state_key, state)
            return {**state, 'state_key': state_key}
        receipt = verify_day(store, result['manifest'], universe, taxonomy, day)
        save(store, prefix + '/days/' + str(day) + '.json', receipt)
        # Queue verified new observations through the existing specialist publisher.
        from specialist_inputs import VERSION as SPECIALIST_VERSION
        window_id = digest({'job': scope, 'universe_hash': digest(universe), 'version': SPECIALIST_VERSION})
        queue_key = 'operations/specialists/publication-queue/' + window_id + '.json'
        if store.get(queue_key) is None:
            write_json(store, queue_key, {'window_id': window_id, 'manifests': [result['manifest']], 'queued_at': now()})
        day += timedelta(days=1)
        state.update(next_date=str(day), status='running', updated_at=now(), last_result=result)
        save(store, state_key, state)
        print(json.dumps({'stage': 'verified_day', **receipt}), flush=True)
    if day < end:
        return {**state, 'state_key': state_key}
    totals, receipt_hashes = {}, []
    day = start
    while day < end:
        receipt = read(store, prefix + '/days/' + str(day) + '.json')
        require(receipt is not None and receipt['date'] == str(day), 'edinet_backfill_day_missing')
        manifest = read(store, receipt['manifest'])
        require(manifest is not None and digest(manifest) == receipt['manifest_sha256'] and
            manifest['status'] == 'complete' and manifest['exhausted'], 'edinet_backfill_manifest_changed')
        head = read(store, 'checkpoints/' + manifest['task_id'] + '/head.json')
        require(head is not None and receipt['manifest'] in head['terminal_history'], 'edinet_backfill_manifest_uncommitted')
        for name, value in receipt.items():
            if isinstance(value, int):
                totals[name] = totals.get(name, 0) + value
        receipt_hashes.append(digest(receipt))
        day += timedelta(days=1)
    gaps = totals.get('source_gaps', 0) + totals.get('no_text_reports', 0) + totals.get('textless_pdf_pages', 0)
    status = 'finished_with_gaps' if gaps else 'complete'
    summary = {'status': status, 'start': str(start), 'end_exclusive': str(end), 'days_verified': len(receipt_hashes),
        'totals': totals, 'receipts_sha256': digest(receipt_hashes), 'scope_note': config['scope_note'], 'verified_at': now()}
    summary_key = prefix + '/completion.json'
    save(store, summary_key, summary)
    subscriptions = [s for p in sns.get_paginator('list_subscriptions_by_topic').paginate(TopicArn=config['email_topic_arn'])
                     for s in p['Subscriptions']]
    require(bool(subscriptions) and all(s['Protocol'] == 'email' and s['Endpoint'] == config['email_recipient'] and
        s['SubscriptionArn'].startswith('arn:') for s in subscriptions), 'edinet_email_subscription_mismatch')
    subject = 'EDINET backfill finished — source or text gaps require review' if gaps else 'EDINET report backfill complete — downloads and extraction verified'
    message = sns.publish(TopicArn=config['email_topic_arn'], Subject=subject,
        Message=f"EDINET backfill {status}.\nRange: {start} through {end - timedelta(days=1)} inclusive.\n\n" +
            json.dumps(totals, indent=2) + '\n\n' + config['scope_note'] + '\nCompletion receipt: ' + summary_key + '\n')
    state.update(status=status, completed_at=now(), completion_key=summary_key, totals=totals,
        notification_message_id=message['MessageId'])
    save(store, state_key, state)
    return {**state, 'state_key': state_key}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='config/edinet-document-backfill.json')
    args = parser.parse_args()
    config = load_json(ROOT / args.config)
    # Share the authenticated lane lock to avoid duplicate daily/historical requests.
    with (ROOT / '.authenticated-job.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({'status': 'partial', 'reason': 'authenticated_lane_busy'}))
            return 2
        import boto3
        settings = StorageSettings.load(ROOT / config['storage_config'])
        result = run(settings.store(), settings, config, load_json(ROOT / config['universe']),
            load_json(ROOT / config['taxonomy']), boto3.client('sns', region_name=settings.region))
        print(json.dumps(result), flush=True)
        return 0 if result['status'] in ('complete', 'finished_with_gaps') else 2


if __name__ == '__main__':
    raise SystemExit(main())
