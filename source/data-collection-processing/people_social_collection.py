#!/usr/bin/env python3
"""Preserve publisher feeds and bounded public social searches as event sources."""
from datetime import date, datetime, timedelta, timezone
import argparse
from email.utils import parsedate_to_datetime
import fcntl
import json
import xml.etree.ElementTree as ET

from collection_operations import load_stored
from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, now, task_spec, write_json
from disclosure_collection import finish_error
from people_movements import DEFAULT_FEEDS, parse_feed
from regulatory_collection import EvidenceClient, SourceIssue, instant, require
from research_contract import ROOT, digest, load_json, seal_record

VERSION = 'people-social-collection-1.0'
PEOPLE_FEEDS = {**DEFAULT_FEEDS,
    'The Robot Report': 'https://www.therobotreport.com/feed/',
    'Semiconductor Engineering': 'https://semiengineering.com/feed/',
    'Energy Storage News': 'https://www.energy-storage.news/feed/',
    'Robohub': 'https://robohub.org/feed/',
    'EE Times': 'https://www.eetimes.com/feed/',
    'pv magazine': 'https://www.pv-magazine.com/feed/'}
SOCIAL_QUERIES = {'biotech': 'biotech', 'robotics': 'robotics',
                  'semiconductors': 'semiconductor', 'energy_storage': '"energy storage"'}
RSS_NOTE = ('Current publisher RSS snapshot; includes general news as source material. '
            'Not verified personnel movements, complete workforce coverage or a historical archive.')
SOCIAL_NOTE = ('Provider search view, not exhaustive platform coverage. Pagination may omit matches; '
               'search uses sortAt, which can differ from createdAt. No inferred sentiment or verified entity links.')


def event_timestamp(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        return None
    return {'value': parsed.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'precision': 'microsecond' if parsed.microsecond else 'second', 'source_timezone': None}


def record(run, identity, url, data, event, evidence, note):
    return seal_record({'document_type': 'collected_record', 'schema_version': '1.0',
        'source': run.spec['source'], 'dataset': run.spec['dataset'], 'source_record_id': identity,
        'source_record_id_basis': 'provider' if run.spec['source'] == 'bluesky_search' else 'documented_composite',
        'source_url': url, 'universe_version': run.universe['universe_version'],
        'company_ids': [], 'listing_ids': [], 'product_ids': [], 'person_ids': [], 'entity_match_status': 'unresolved',
        'event_at': event, 'available_at': None, 'source_updated_at': None,
        'ingested_at': now(), 'availability_basis': 'unknown', 'availability_evidence': [], 'run_id': run.run_id,
        'payload': {'data': data, 'coverage_note': note, 'source_evidence': list(evidence)}})


def collect_feed(store, settings, universe, taxonomy, name, url, day, client=None, capture_full_text=True):
    require(day == datetime.now(timezone.utc).date(), 'rss_snapshot_cannot_be_backdated')
    spec = task_spec('people_rss', 'people_source_records', 'daily', instant(day), instant(day + timedelta(days=1)),
        {'feed_name': name, 'feed_url': url, 'coverage': 'current_feed_snapshot', **({'full_text_pipeline_version': 'people-rss-fulltext-1.0'} if capture_full_text else {})}, VERSION, universe, taxonomy)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=True)
    except AlreadyComplete as exc:
        return {'status': 'complete', 'manifest': str(exc), 'already_complete': True}
    client = client or EvidenceClient(store, 'people_rss')
    content_lock = None
    try:
        if not run.exhausted:
            raw = client.get(url)
            require(ET.fromstring(raw).tag.rsplit('}', 1)[-1] in {'rss', 'feed', 'RDF'}, 'rss_invalid_document')
            entries = parse_feed(raw, name)
            records, seen = [], set()
            listing_evidence = list(client.evidence)
            from people_rss_content import Capture, VERSION as CONTENT_VERSION, apply
            capture = Capture(store, None, max_publisher_requests=10)
            # All publisher captures share a durable daily budget. If news is
            # using it, retain discovery and let the content worker retry.
            content_lock = (ROOT / '.news-collection.lock').open('a')
            self_budget_lock = False
            if capture_full_text:
                try:
                    fcntl.flock(content_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self_budget_lock = True
                except BlockingIOError:
                    pass
            for entry in entries:
                require(entry['url'].startswith(('https://', 'http://')), 'rss_missing_public_url')
                identity = digest({'publisher': name, 'url': entry['url']})
                require(identity not in seen, 'rss_duplicate_item_requires_review')
                seen.add(identity)
                output = record(run, identity, entry['url'], entry, event_timestamp(entry['publishedAt']), listing_evidence, RSS_NOTE)
                if capture_full_text:
                    try:
                        if not self_budget_lock:
                            raise SourceIssue('fulltext_runner_busy', True)
                        body = capture.get(entry, historical=False)
                    except SourceIssue as exc:
                        if not exc.partial:
                            raise
                        body = {'version': CONTENT_VERSION, 'status': 'pending', 'article_url': entry['url'],
                            'captured_at': now(), 'source_evidence': [], 'text_characters': 0, 'reason': exc.code}
                    output = apply(output, body, store)
                records.append(output)
            content_lock.close()
            run.commit_page(records, next_cursor=None, exhausted=True)
        return {'status': 'complete', 'records': run.state['record_count'],
                'manifest': run.finish('complete', expected_records=run.state['record_count'])}
    except (Exception, KeyboardInterrupt) as exc:
        return finish_error(run, exc, client.evidence)
    finally:
        if content_lock is not None:
            content_lock.close()


def collect_social(store, settings, universe, taxonomy, sector, query, day, client=None, max_pages=10):
    require(date(2021, 1, 1) <= day < datetime.now(timezone.utc).date(), 'social_requires_closed_daily_window')
    spec = task_spec('bluesky_search', 'social_records', 'daily', instant(day), instant(day + timedelta(days=1)),
        {'query': query, 'candidate_sector': sector, 'sort': 'latest', 'date_basis': 'provider_sortAt',
         'coverage': 'provider_search_view_not_exhaustive'}, VERSION, universe, taxonomy)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=True)
    except AlreadyComplete as exc:
        return {'status': 'complete', 'manifest': str(exc), 'already_complete': True}
    client = client or EvidenceClient(store, 'bluesky_search')
    try:
        seen = set()
        for page in run.state['pages']:
            for batch in page['batches']:
                seen.update(json.loads(line)['source_record_id'] for line in store.get(batch['key']).body.splitlines())
        for _ in range(max_pages):
            if run.exhausted:
                return {'status': 'complete', 'records': run.state['record_count'],
                        'manifest': run.finish('complete', expected_records=run.state['record_count'])}
            params = {'q': query, 'sort': 'latest', 'since': instant(day),
                      'until': instant(day + timedelta(days=1)), 'limit': 100}
            if run.cursor:
                params['cursor'] = run.cursor
            client.evidence = []
            result = json.loads(client.get('https://api.bsky.app/xrpc/app.bsky.feed.searchPosts', params))
            posts = result.get('posts'); require(isinstance(posts, list), 'social_invalid_response')
            cursor = result.get('cursor')
            require(not cursor or (isinstance(cursor, str) and cursor != run.cursor), 'social_cursor_stalled')
            records = []
            for post in posts:
                uri = post.get('uri', ''); author = post.get('author', {}).get('did', '')
                require(uri.startswith('at://') and author.startswith('did:') and isinstance(post.get('record'), dict), 'social_invalid_post')
                require(uri not in seen, 'social_duplicate_during_scan')
                seen.add(uri)
                url = 'https://bsky.app/profile/' + author + '/post/' + uri.rsplit('/', 1)[-1]
                records.append(record(run, uri, url, post, event_timestamp(post['record'].get('createdAt')),
                                      client.evidence, SOCIAL_NOTE))
            run.commit_page(records, next_cursor=cursor or None, exhausted=not cursor)
        if run.exhausted:
            return {'status': 'complete', 'records': run.state['record_count'],
                    'manifest': run.finish('complete', expected_records=run.state['record_count'])}
        raise SourceIssue('social_page_budget', True)
    except (Exception, KeyboardInterrupt) as exc:
        return finish_error(run, exc, client.evidence)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--feeds-only', action='store_true', help='Skip social sources pending verified access')
    parser.add_argument('--social-only', action='store_true', help='Run social sources without repeating personnel feeds')
    args = parser.parse_args()
    with (ROOT / '.people-social.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 2
        settings = StorageSettings.load(ROOT / 'config/collection-storage.s3.json'); store = settings.store()
        universe = load_json(ROOT / 'config/company-universe.v0.3.json'); taxonomy = load_json(ROOT / 'config/sectors.v1.json')
        today = datetime.now(timezone.utc).date(); outcomes = []
        for name, url in ({} if args.social_only else PEOPLE_FEEDS).items():
            result = {'source': name, **collect_feed(store, settings, universe, taxonomy, name, url, today)}
            outcomes.append(result); print(json.dumps(result), flush=True)
        for sector, query in ({} if args.feeds_only else SOCIAL_QUERIES).items():
            identity = digest({'version': VERSION, 'sector': sector, 'query': query, 'universe': digest(universe),
                               'taxonomy': digest(taxonomy), 'origin': '2026-09-23'})
            key = 'operations/social/daily/' + identity + '.json'
            state, token = load_stored(store, key)
            day = date.fromisoformat(state['next_date']) if state else date(2026, 9, 23)
            if day >= today:
                continue
            result = {'source': 'bluesky', 'sector': sector, 'day': str(day),
                      **collect_social(store, settings, universe, taxonomy, sector, query, day)}
            if result['status'] == 'complete':
                write_json(store, key, {'next_date': str(day + timedelta(days=1)), 'manifest': result['manifest']}, token)
            outcomes.append(result); print(json.dumps(result), flush=True)
        summary = {'checked_at': now(), 'outcomes': outcomes,
                   'history_status': 'RSS has no verified archive; Bluesky 2021 history unavailable. Licensed archives required for missing periods.'}
        write_json(store, 'operations/people-social/attempts/' + digest(summary) + '.json', summary)
        return int(any(r['status'] != 'complete' for r in outcomes))


if __name__ == '__main__':
    raise SystemExit(main())
