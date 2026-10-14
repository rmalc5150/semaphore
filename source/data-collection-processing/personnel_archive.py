#!/usr/bin/env python3
"""Preserve personnel-related archive source records for later event review.

This is a lexical retrieval filter, not a personnel-event extractor or model.
It preserves the complete parent record, source-document references and dates.
"""
import argparse
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import re
import tempfile

from collection_operations import load_stored
from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, now, task_spec, write_json
from disclosure_collection import finish_error
from regulatory_athena import read_inputs
from research_contract import ROOT, canonical_json, digest, load_json, seal_record
from window_publication import list_keys

VERSION = 'personnel-archive-2.1'
INPUTS = {('finlight', 'news_articles'), ('marketaux', 'news_articles'),
          ('disclosure_documents', 'documents'), ('hkex_news', 'filings'), ('people_rss', 'people_source_records')}
ROLE = re.compile(r'\b(?:chief|CEO|CFO|CTO|CSO|CMO|COO|presidents?|directors?|officers?|executives?|employees?|scientists?|engineers?|workforce|staff|leadership|board|talent|roles?|jobs?|apprentices?|chair(?:man|woman|person)?)\b', re.I)
MOVE = re.compile(r'\b(?:appoint\w*|nam(?:e|es|ed|ing)|hir(?:e|es|ed|ing)|join(?:s|ed|ing)?|resign\w*|retir\w*|depart\w*|succe(?:ed\w*|ssion|ssor)|promot\w*|layoffs?|laying off|laid off|redundan\w*|restructur\w*|step(?:s|ped|ping)? down|workforce reduction)\b', re.I)
DIRECT = re.compile(r'\b(?:layoffs?|laid off|workforce reduction|headcount|employee count|item\s+5\.02)\b|委任|辞任|辭任|离任|離任|裁员|裁員', re.I)
NOTE = ('Personnel-source retrieval candidate, not a verified movement or unified event. '
        'Lexical screening of complete stored source windows can miss announcements and retain false positives. '
        'Historical coverage is limited to available parent archives; current metadata is not backdated.')


def searchable(record):
    payload = record['payload']; data = payload.get('data', {})
    fields = [payload.get('title')]
    if isinstance(data, dict):
        fields += [data.get(k) for k in ('title', 'description', 'snippet', 'text', 'content', 'body', 'TITLE')]
    return '\n'.join(v for v in fields if isinstance(v, str))


def match_terms(record):
    text = re.sub(r'[-‐‑‒–—]', ' ', searchable(record))
    direct = DIRECT.search(text)
    if direct:
        return [direct.group()]
    # Require role and change language within a bounded passage, not merely in
    # unrelated sections of a long annual report.
    for move in MOVE.finditer(text):
        role = ROLE.search(text[max(0, move.start() - 180):move.end() + 180])
        if role:
            return [move.group(), role.group()]
    return []



def retrieval_context(record):
    text = re.sub(r'[-‐‑‒–—]', ' ', searchable(record))
    flags = ['unreviewed_source_candidate']
    if re.search(r'\b(?:without|no|avoid(?:ing|ed)?)\s+(?:planned\s+)?layoffs?\b', text, re.I):
        flags.append('negated_or_avoided_layoffs')
    if re.search(r'\b(?:jobs?|roles?|vacanc(?:y|ies)|job postings?)\b', text, re.I):
        flags.append('job_openings_not_confirmed_hires')
    if not record.get('company_ids'):
        flags.append('company_match_unresolved')
    if record.get('payload', {}).get('candidate_sector_ids'):
        flags.append('search_sector_is_not_verified_company_sector')
    return flags


def collect(store, settings, key):
    raw = store.get(key)
    if raw is None:
        raise ValueError('Missing archive manifest')
    parent_manifest = json.loads(raw.body); parent_task = parent_manifest['task']
    if (parent_task['source'], parent_task['dataset']) not in INPUTS:
        raise ValueError('Unsupported personnel archive source')
    # Spool selected source records to disk while validating the whole parent
    # window. No candidate run is committed until validation succeeds.
    with tempfile.TemporaryFile() as spool:
        stats = {'undated_skipped': 0, 'before_floor_skipped': 0}
        def consume(entry):
            parent = entry['record']; event = parent['event_at']
            if not event:
                stats['undated_skipped'] += 1
                return
            if event['value'][:10] < '2021-01-01':
                stats['before_floor_skipped'] += 1
                return
            terms = match_terms(parent)
            if terms:
                spool.write(canonical_json({'record': parent, 'batches': sorted(entry['batches']), 'terms': terms}) + b'\n')
        _, universe, inputs = read_inputs(store, [key], allowed={parent_task['source']},
                                          dataset=parent_task['dataset'], consume=consume)
        taxonomy = json.loads(store.get('manifests/configurations/taxonomy/' + parent_task['taxonomy_hash'] + '.json').body)
        scope = {'parent_manifest': key, 'parent_manifest_sha256': hashlib.sha256(raw.body).hexdigest(),
                 'retrieval_version': VERSION, 'coverage': NOTE, 'historical_floor': '2021-01-01',
                 'input_records': inputs[0]['records'], **stats}
        spec = task_spec('personnel_archive', 'people_source_records', parent_task['mode'],
            parent_task['window']['start'], parent_task['window']['end'], scope, VERSION, universe, taxonomy)
        try:
            run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=True)
        except AlreadyComplete as exc:
            return {'status': 'complete', 'manifest': str(exc), 'already_complete': True}
        try:
            if not run.exhausted:
                spool.seek(0); records = []; buffered_bytes = 0
                offset = int(run.cursor or 0); position = 0
                for position, line in enumerate(spool, 1):
                    if position <= offset:
                        continue
                    entry = json.loads(line); parent = entry['record']; oid = parent['observation_id']
                    output = seal_record({'document_type': 'collected_record', 'schema_version': '1.0',
                        'source': 'personnel_archive', 'dataset': 'people_source_records', 'source_record_id': oid,
                        'source_record_id_basis': 'documented_composite', 'source_url': parent['source_url'],
                        'universe_version': universe['universe_version'],
                        **{k: parent[k] for k in ('company_ids', 'listing_ids', 'product_ids', 'person_ids', 'entity_match_status')},
                        'event_at': parent['event_at'], 'source_updated_at': parent['source_updated_at'], 'available_at': None,
                        'ingested_at': now(), 'availability_basis': 'unknown', 'availability_evidence': [], 'run_id': run.run_id,
                        'payload': {'data': parent, 'retrieval_terms': entry['terms'], 'review_status': 'unreviewed_source_candidate',
                            'retrieval_context': retrieval_context(parent),
                            'parent_manifest': key, 'parent_record_id': parent['record_id'], 'parent_observation_id': oid,
                            'parent_batch_keys': entry['batches'], 'coverage_note': NOTE,
                            'source_evidence': parent['payload']['source_evidence']}})
                    records.append(output); buffered_bytes += len(canonical_json(output))
                    if len(records) >= 32 or buffered_bytes >= 2 * 1024 * 1024:
                        run.commit_page(records, next_cursor=str(position), exhausted=False)
                        records = []; buffered_bytes = 0
                run.commit_page(records, next_cursor=None, exhausted=True)
            return {'status': 'complete', 'input_records': inputs[0]['records'], 'records': run.state['record_count'],
                    **stats, 'manifest': run.finish('complete', expected_records=run.state['record_count'])}
        except (Exception, KeyboardInterrupt) as exc:
            return finish_error(run, exc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-windows', type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.max_windows <= 24:
        parser.error('max-windows must be 1..24')
    with (ROOT / '.personnel-archive.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 2
        settings = StorageSettings.load(ROOT / 'config/collection-storage.s3.json'); store = settings.store()
        candidates = []
        for key in list_keys(store, settings, 'checkpoints/' if hasattr(store, 'root') else 'checkpoints/task_'):
            if not key.startswith('checkpoints/task_') or not key.endswith('/head.json'):
                continue
            head, _ = load_stored(store, key); task = head.get('task', {})
            if head.get('status') == 'complete' and (task.get('source'), task.get('dataset')) in INPUTS:
                if task['window']['end'] > '2021-01-01T00:00:00Z':
                    candidates.append((task['window']['start'], task['source'], head['terminal_manifest']))
        lanes = defaultdict(deque)
        for start, source, key in sorted(candidates):
            lanes[source].append(key)
        ordered = []
        while any(lanes.values()):
            for source in sorted(lanes):
                if lanes[source]:
                    ordered.append(lanes[source].popleft())
        outcomes = []
        for key in ordered:
            receipt_key = 'operations/personnel-archive/processed/' + digest([VERSION, key]) + '.json'
            receipt, token = load_stored(store, receipt_key)
            if receipt:
                continue
            retry_key = 'operations/personnel-archive/retries/' + digest([VERSION, key]) + '.json'
            retry, retry_token = load_stored(store, retry_key)
            if retry and retry['retry_after'] > now():
                continue
            try:
                result = collect(store, settings, key)
                if result['status'] == 'complete':
                    write_json(store, receipt_key, {**result, 'input_manifest': key, 'checked_at': now()}, token)
            except Exception as exc:
                result = {'status': 'failed', 'error_type': type(exc).__name__, 'input_manifest': key}
            if result['status'] != 'complete':
                write_json(store, retry_key, {**result,
                    'retry_after': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace('+00:00', 'Z')}, retry_token)
            outcomes.append(result); print(json.dumps(result), flush=True)
            if len(outcomes) >= args.max_windows:
                break
        return int(any(r['status'] != 'complete' for r in outcomes))


if __name__ == '__main__':
    raise SystemExit(main())
