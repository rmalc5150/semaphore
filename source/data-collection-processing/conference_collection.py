#!/usr/bin/env python3
"""Collect DOI-registered proceedings with bounded, auditable daily windows."""
from datetime import date, datetime, timedelta, timezone
import fcntl
import json
from urllib.parse import quote

from collection_operations import load_stored
from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, now, task_spec, write_json
from disclosure_collection import finish_error
from regulatory_collection import EvidenceClient, SourceIssue, instant, require
from research_contract import ROOT, digest, load_json, seal_record

SOURCE = 'crossref_proceedings'
VERSION = 'conference-collection-1.0'
NOTE = ('DOI-registered proceedings-article metadata only; excludes unregistered presentations and '
        'many journal-supplement abstracts. Current metadata is not a historical snapshot. '
        'DOI registration, publication and conference dates are distinct; availability is unverified.')


def publication(row):
    parts = (row.get('published') or {}).get('date-parts', [[]])[0]
    if len(parts) != 3:
        return None
    return {'value': date(*parts).isoformat(), 'precision': 'day', 'source_timezone': None}


def collect(store, settings, universe, taxonomy, start, end, mode, client=None, max_pages=240, rows=500):
    require(end == start + timedelta(days=1), 'conference_requires_single_day_window')
    require(start >= date(2021, 1, 1), 'conference_before_historical_floor')
    basis = 'pub' if mode == 'historical' else 'update'
    scope = {'type': 'proceedings-article', 'date_filter': basis, 'selection': 'all', 'rows': rows}
    spec = task_spec(SOURCE, 'conference_records', mode, instant(start), instant(end), scope, VERSION, universe, taxonomy)
    head, _ = load_stored(store, 'checkpoints/task_' + digest(spec) + '/head.json')
    # Crossref cursors are temporary. Restart an unfinished single-day query from
    # its beginning; immutable earlier attempts remain available for inspection.
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings,
            refresh=bool(head and head['status'] != 'complete'))
    except AlreadyComplete as exc:
        return {'status': 'complete', 'manifest': str(exc), 'already_complete': True}
    client = client or EvidenceClient(store, SOURCE)
    seen, cursor, total = set(), '*', None
    try:
        for _ in range(max_pages):
            params = {'filter': f'type:proceedings-article,from-{basis}-date:{start},until-{basis}-date:{start}',
                'rows': rows, 'cursor': cursor, 'mailto': 'support@optima-holdings.com'}
            client.evidence = []
            response = json.loads(client.get('https://api.crossref.org/works', params))
            require(response.get('status') == 'ok', 'conference_invalid_response')
            message = response['message']; items = message['items']
            count = message['total-results']
            require(type(count) is int and count >= 0 and isinstance(items, list), 'conference_invalid_counts')
            require(total is None or total == count, 'conference_results_changed_during_scan')
            total = count
            records = []
            for row in items:
                doi = row.get('DOI', '').strip().lower()
                require(doi.startswith('10.') and '/' in doi and row.get('type') == 'proceedings-article', 'conference_invalid_work')
                require(doi not in seen, 'conference_duplicate_during_scan')
                seen.add(doi)
                event = publication(row)
                # Partial publication dates remain raw; never invent January 1.
                if mode == 'historical' and event:
                    require(start <= date.fromisoformat(event['value']) < end, 'conference_publication_outside_window')
                records.append(seal_record({'document_type': 'collected_record', 'schema_version': '1.0',
                    'source': SOURCE, 'dataset': 'conference_records', 'source_record_id': doi,
                    'source_record_id_basis': 'provider', 'source_url': 'https://doi.org/' + quote(doi, safe='/'),
                    'universe_version': universe['universe_version'], 'company_ids': [], 'listing_ids': [],
                    'product_ids': [], 'person_ids': [], 'entity_match_status': 'unresolved',
                    'event_at': event, 'source_updated_at': None, 'available_at': None,
                    'availability_basis': 'unknown', 'availability_evidence': [], 'ingested_at': now(),
                    'run_id': run.run_id, 'payload': {'record_type': 'conference_publication',
                        'title': (row.get('title') or [None])[0], 'date_basis': 'provider_published_date',
                        'data': row, 'coverage_note': NOTE, 'source_evidence': list(client.evidence)}}))
            exhausted = len(items) < rows
            if exhausted:
                require(len(seen) == total, 'conference_total_mismatch')
            cursor = message.get('next-cursor')
            require(exhausted or cursor, 'conference_missing_cursor')
            run.commit_page(records, next_cursor=cursor if not exhausted else None, exhausted=exhausted)
            print(json.dumps({'stage': 'conference_page', 'mode': mode, 'day': str(start),
                'records': len(seen), 'provider_total': total, 'exhausted': exhausted}), flush=True)
            if exhausted:
                return {'status': 'complete', 'records': len(seen), 'manifest': run.finish('complete', expected_records=total)}
        raise SourceIssue('conference_page_budget', True)
    except (Exception, KeyboardInterrupt) as exc:
        return finish_error(run, exc, client.evidence)


def advance(store, settings, universe, taxonomy, mode, origin, end):
    identity = digest({'version': VERSION, 'daily_filter': 'update', 'universe': digest(universe), 'taxonomy': digest(taxonomy),
                       'mode': mode, 'origin': str(origin)})
    key = f'operations/conferences/progress/{identity}.json'
    state, token = load_stored(store, key)
    day = date.fromisoformat(state['next_date']) if state else origin
    if day >= end:
        return {'status': 'caught_up', 'mode': mode, 'next_date': str(day)}
    result = collect(store, settings, universe, taxonomy, day, day + timedelta(days=1), mode)
    if result['status'] == 'complete':
        manifest, _ = load_stored(store, result['manifest'])
        wid = digest(manifest['task'])
        queue_key = f'operations/conferences/publication-queue/{wid}.json'
        previous, queue_token = load_stored(store, queue_key)
        if not previous or previous['manifests'] != [result['manifest']]:
            write_json(store, queue_key, {'window_id': wid, 'manifests': [result['manifest']], 'queued_at': now()}, queue_token)
        write_json(store, key, {'next_date': str(day + timedelta(days=1)), 'last_manifest': result['manifest'], 'updated_at': now()}, token)
    return {**result, 'mode': mode, 'day': str(day)}


def main():
    with (ROOT / '.conference-collection.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 2
        settings = StorageSettings.load(ROOT / 'config/collection-storage.s3.json')
        store = settings.store()
        universe = load_json(ROOT / 'config/company-universe.v0.3.json')
        taxonomy = load_json(ROOT / 'config/sectors.v1.json')
        today = datetime.now(timezone.utc).date()
        origin = date(2026, 9, 23)
        results = [advance(store, settings, universe, taxonomy, 'daily', origin, today),
                   advance(store, settings, universe, taxonomy, 'historical', date(2021, 1, 1), origin)]
        print(json.dumps(results), flush=True)
        return int(any(r['status'] not in {'complete', 'caught_up'} for r in results))


if __name__ == '__main__':
    raise SystemExit(main())
