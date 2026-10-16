#!/usr/bin/env python3
"""Bounded S11 full-content backfill and daily capture with verified completion email."""
import argparse
from datetime import date, datetime, timedelta
import fcntl
import hashlib
import json

import disclosure_collection as d
import sec_filings as sec
from collection_storage import StorageSettings, now, write_json
from research_contract import ROOT, digest, load_json
from regulatory_collection import EvidenceClient, require

STAGES = ('sec', 'hkex', 'documents', *d.CATEGORIES)


def read(store, key):
    obj = store.get(key)
    return json.loads(obj.body) if obj else None


def save(store, key, value):
    obj = store.get(key)
    write_json(store, key, value, obj.token if obj else None)


def prefix_for(config, universe, taxonomy, mode):
    identity = digest({'config': config, 'content_version': d.CONTENT_VERSION,
        'universe': digest(universe), 'taxonomy': digest(taxonomy), 'mode': mode})
    return 'operations/s11-content/' + mode + '/' + identity


def run_stage(stage, day, mode, stages, store, settings, config, universe, taxonomy, cache):
    end = day + timedelta(days=1)
    if stage == 'sec':
        matcher = sec.CompanyMatcher(universe)
        scope = {'selection': 'universe', 'company_ids': sorted(matcher.companies), 'sectors': [],
            'ciks': [], 'forms': list(config['sec_forms']), 'date_basis': 'filing_date_america_new_york'}
        return sec.collect_window(store, settings, universe, taxonomy, sec.SECClient(config['sec_user_agent']),
            day, end, mode, scope, matcher, cache, max_records=config['records_per_stage'])
    if stage == 'hkex':
        cache.clear()  # Release the large SEC quarterly index before downstream validation.
        return d.collect_hkex(store, settings, universe, taxonomy, day, end, mode,
            selection='universe', page_size=100, max_pages=config['hkex_pages_per_invocation'])
    parents = [stages[s]['manifest'] for s in ('sec', 'hkex')] if stage == 'documents' else [stages['documents']['manifest']]
    sources = ['sec_edgar', 'hkex_news'] if stage == 'documents' else ['disclosure_documents']
    return d.collect_derived(store, settings, universe, taxonomy, day, end, mode, stage, parents, sources,
        selection='universe', max_records=config['records_per_stage'], sec_forms=tuple(config['sec_forms']))


def verify_day(store, stages, universe, taxonomy, day):
    keys = [stages[s]['manifest'] for s in STAGES]
    entries, _, manifests = d.read_inputs(store, keys, universe, taxonomy)
    d.check_coverage(manifests, day, day + timedelta(days=1),
        ['sec_edgar', 'hkex_news', 'disclosure_documents', 'disclosure_candidates'])
    require(all(m['status'] == 'complete' and m['exhausted'] for m in manifests), 's11_incomplete_stage')
    counts = {'documents': 0, 'candidates': 0, 'text_characters': 0, 'chunks': 0,
        'textless_pdf_pages': 0, 'unsupported_content_files': 0, 'unresolved_company_documents': 0}
    contents = {}
    for entry in entries:
        record = entry['record']
        if record['source'] not in ('disclosure_documents', 'disclosure_candidates'):
            continue
        p = record['payload']
        require(p.get('content_pipeline_version') == d.CONTENT_VERSION, 's11_old_content_pipeline')
        ref = p.get('content_reference')
        require(ref and ref in p['source_evidence'], 's11_full_content_reference_missing')
        pair = (ref['key'], ref['sha256'])
        if pair not in contents:
            content = json.loads(d.get_bytes(store, ref['key'], ref['sha256']))
            require(content['version'] == d.CONTENT_VERSION and hashlib.sha256(content['text'].encode()).hexdigest() ==
                content['text_sha256'], 's11_full_content_integrity')
            units = {u['document_id']: u for u in content['documents']}
            for chunk in content['chunks']:
                unit = units[chunk['document_id']]
                require(0 <= chunk['start'] < chunk['end'] <= len(unit['text']), 's11_chunk_out_of_bounds')
            contents[pair] = content
        content = contents[pair]
        if record['source'] == 'disclosure_documents':
            require(p['data']['text'] is None or p['data']['text'] == content['text'], 's11_document_text_mismatch')
            require(p['data']['text_sha256'] == content['text_sha256'], 's11_document_text_hash_mismatch')
            counts['documents'] += 1
            counts['text_characters'] += len(content['text'])
            counts['chunks'] += len(content['chunks'])
            counts['textless_pdf_pages'] += content['textless_pdf_pages']
            counts['unsupported_content_files'] += sum(not f['filename'].lower().endswith(('.gif', '.jpg', '.jpeg', '.png', '.svg'))
                for f in content['extraction']['skipped_files'])
            counts['unresolved_company_documents'] += int(record['entity_match_status'] != 'matched')
        else:
            require(p['data']['classification_basis'] == 'source_text_passages' and p['data']['matches'], 's11_form_only_candidate')
            for match in p['data']['matches']:
                require(match['excerpt'] and match['excerpt'] == content['text'][match['start']:match['end']] and
                    match['document'] is not None and match['chunk_ids'], 's11_candidate_passage_invalid')
            counts['candidates'] += 1
    return {'date': str(day), 'manifests': [{'key': key, 'sha256': digest(read(store, key))} for key in keys],
        'verified_at': now(), **counts}


def run(store, settings, config, universe, taxonomy, sns, mode='historical', stage_runner=run_stage, verifier=verify_day):
    start = date.fromisoformat(config['start'] if mode == 'historical' else config['daily_start'])
    end = date.fromisoformat(config['end_exclusive']) if mode == 'historical' else min(date.today(),
        datetime.now(sec.NY).date())
    require(start <= end <= date.today(), 's11_invalid_window')
    prefix = prefix_for(config, universe, taxonomy, mode)
    state_key = prefix + '/state.json'
    state = read(store, state_key) or {'next_date': str(start), 'status': 'running', 'started_at': now(), 'stages': {}}
    if state.get('notification_message_id'):
        return state
    day, cache = date.fromisoformat(state['next_date']), {}
    require(start <= day <= end, 's11_invalid_cursor')
    for _ in range(config['max_days_per_invocation']):
        if day >= end:
            break
        stages = state.setdefault('stages', {})
        for stage in STAGES:
            if stages.get(stage, {}).get('status') == 'complete':
                continue
            result = stage_runner(stage, day, mode, stages, store, settings, config, universe, taxonomy, cache)
            result = {k: v for k, v in result.items() if k in
                ('status', 'manifest', 'records', 'reason', 'already_complete', 'selected_filings')}
            stages[stage] = result
            state.update(status=result['status'], updated_at=now())
            save(store, state_key, state)
            print(json.dumps({'stage': stage, 'date': str(day), **result}), flush=True)
            if result['status'] != 'complete':
                return {**state, 'state_key': state_key}
        receipt = verifier(store, stages, universe, taxonomy, day)
        save(store, prefix + '/days/' + str(day) + '.json', receipt)
        day += timedelta(days=1)
        state.update(next_date=str(day), stages={}, status='running', updated_at=now())
        save(store, state_key, state)
        print(json.dumps({'stage': 'verified_day', **receipt}), flush=True)
    if day < end or mode == 'daily':
        state['status'] = 'caught_up' if day >= end else 'partial'
        save(store, state_key, state)
        return {**state, 'state_key': state_key}
    totals, receipt_hashes, day = {}, [], start
    while day < end:
        receipt = read(store, prefix + '/days/' + str(day) + '.json')
        require(receipt is not None and receipt['date'] == str(day), 's11_missing_day')
        for ref in receipt['manifests']:
            manifest = read(store, ref['key'])
            require(manifest is not None and digest(manifest) == ref['sha256'] and manifest['status'] == 'complete'
                    and manifest['exhausted'], 's11_manifest_changed_or_incomplete')
            head = read(store, 'checkpoints/' + manifest['task_id'] + '/head.json')
            require(head is not None and ref['key'] in head['terminal_history'], 's11_manifest_not_committed')
        for name, value in receipt.items():
            if isinstance(value, int):
                totals[name] = totals.get(name, 0) + value
        receipt_hashes.append(digest(receipt))
        day += timedelta(days=1)
    gaps = totals.get('textless_pdf_pages', 0) + totals.get('unsupported_content_files', 0)
    status = 'finished_with_gaps' if gaps else 'complete'
    summary = {'status': status, 'start': str(start), 'end_exclusive': str(end), 'days_verified': len(receipt_hashes),
        'totals': totals, 'receipt_hashes_sha256': digest(receipt_hashes), 'scope_note': config['scope_note'], 'verified_at': now()}
    summary_key = prefix + '/completion.json'
    save(store, summary_key, summary)
    subscriptions = [s for page in sns.get_paginator('list_subscriptions_by_topic').paginate(TopicArn=config['email_topic_arn'])
        for s in page['Subscriptions']]
    require(bool(subscriptions) and all(s['Protocol'] == 'email' and s['Endpoint'] == config['email_recipient'] and
        s['SubscriptionArn'].startswith('arn:') for s in subscriptions), 's11_email_subscription_mismatch')
    message = sns.publish(TopicArn=config['email_topic_arn'],
        Subject='S11 content backfill finished — extraction gaps recorded' if gaps else 'S11 full-content backfill complete — verified',
        Message=f"S11 backfill {status}.\nRange: {start} through {end - timedelta(days=1)} inclusive.\n\n" +
            json.dumps(totals, indent=2) + '\n\n' + config['scope_note'] + '\nCompletion receipt: ' + summary_key)
    state.update(status=status, completion_key=summary_key, completed_at=now(), totals=totals,
        notification_message_id=message['MessageId'])
    save(store, state_key, state)
    return {**state, 'state_key': state_key}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('historical', 'daily'), default='historical')
    parser.add_argument('--config', default='config/s11-content-backfill.json')
    args = parser.parse_args()
    config = load_json(ROOT / args.config)
    # Serialize with the existing source runner, preserving its cursors and schedules.
    with (ROOT / '.collection-operations.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({'status': 'partial', 'reason': 'runner_already_active'}))
            return 2
        import boto3
        settings = StorageSettings.load(ROOT / config['storage_config'])
        result = run(settings.store(), settings, config, load_json(ROOT / config['universe']),
            load_json(ROOT / config['taxonomy']), boto3.client('sns', region_name=settings.region), args.mode)
        print(json.dumps(result), flush=True)
        return 0 if result['status'] in ('complete', 'finished_with_gaps', 'caught_up') else 2


if __name__ == '__main__':
    raise SystemExit(main())
