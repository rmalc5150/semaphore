"""Collect OpenAlex works and KAKEN projects with durable, bounded S3 checkpoints."""

import argparse
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import time
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError
import requests

from constellation.control import Control, canonical
from constellation.worker import put_verified

OPENALEX = 'openalex_scholarly_graph'
KAKEN = 'japan_kaken_funded_research'
URLS = {OPENALEX: 'https://api.openalex.org/works', KAKEN: 'https://kaken.nii.ac.jp/opensearch/'}
FIELDS = {OPENALEX: 'openalex-api-key', KAKEN: 'kaken-app-id'}
FLOOR = date(2016, 1, 1)
DAILY_ORIGIN = date(2026, 11, 19)
SNAPSHOT_DATE = date(2026, 10, 14)
SNAPSHOT_BUCKET = 'openalex'
SNAPSHOT_DIR = 'data/jsonl/works/'
SNAPSHOT_KEY = SNAPSHOT_DIR + 'manifest.json'
SNAPSHOT_PARTS = 1898
SNAPSHOT_FILE = re.compile(r'data/jsonl/works/updated_date=\d{4}-\d{2}-\d{2}/part_\d+\.gz')
OPENALEX_ID = re.compile(r'https://openalex\.org/W[1-9]\d*')
KAKEN_ID = re.compile(r'KAKENHI-[A-Z]+-[A-Za-z0-9-]+')
OPENALEX_PAGE_SIZE = 100
KAKEN_PAGE_SIZE = 100
MAX_RESPONSE = 32 * 1024**2
BATCH_PAGES = 20
MAX_BATCH = 8 * 1024**2
AGENT = 'ConstellationResearch/1.0 (support@optima-holdings.com)'
OPENALEX_LIMITS = {'daily': 7300, 'bridge': 2100}
JAPAN = ZoneInfo('Asia/Tokyo')
BATCH_PAUSE = Path('/opt/constellation/batch-paused')


class FeedError(Exception):
    """An operational error safe to include in a receipt or service log."""


class Deferred(FeedError):
    pass


class Evidence:
    def __init__(self, control):
        self.control = control
        self.s3 = control.s3
        self.bucket = control.config['bucket']
        self.prefix = control.config['prefix'] + '/research-feeds/v1'

    def uri(self, key):
        return f's3://{self.bucket}/{self.prefix}/{key}'

    def state(self, key):
        key = self.prefix + '/' + key
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            code = error.response['Error']['Code']
            if code in {'NoSuchKey', '404'}:
                return None, None
            if code != 'AccessDenied':
                raise
            # C7's prefix-scoped policy can return a 403 for an absent key.
            listing = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=key, MaxKeys=1)
            if any(item['Key'] == key for item in listing.get('Contents', [])):
                raise
            return None, None
        with response['Body'] as body:
            return json.load(body), response['ETag']

    def save(self, key, value, etag):
        data = canonical(value)
        try:
            result = self.s3.put_object(
                Bucket=self.bucket, Key=self.prefix + '/' + key, Body=data,
                ContentType='application/json', ServerSideEncryption='AES256',
                **({'IfMatch': etag} if etag else {'IfNoneMatch': '*'}),
            )
        except Exception:
            current, token = self.state(key)
            if current != value:
                raise
            return token
        return result['ETag']

    def immutable(self, key, data, media):
        return put_verified(self.control, self.prefix + '/' + key, data, media)

    def publish(self, source, mode, name, uris):
        if not uris:
            return
        body = ('\n'.join(uris) + '\n').encode()
        self.immutable(f'published/{source}/{mode}/{name}.manifest', body, 'text/plain')


def history_pending(control):
    """Expose outstanding backfills to the existing C7 wake and drain policy."""
    evidence = Evidence(control)
    enabled, _ = evidence.state('control.json')
    if not enabled or not enabled.get('historical_enabled') or not control.allowed():
        return False
    snapshot, _ = evidence.state(f'progress/{OPENALEX}/snapshot.json')
    if (snapshot or {}).get('next_part', 0) < SNAPSHOT_PARTS:
        return True
    progress, _ = evidence.state(f'progress/{KAKEN}/historical.json')
    year = int(progress['next']) if progress else FLOOR.year
    if year >= fiscal_year(datetime.now(JAPAN).date()):
        return False
    checkpoint, _ = evidence.state(f'checkpoints/{KAKEN}/historical/fy-{year}.json')
    return not (checkpoint and checkpoint.get('exhausted') and checkpoint.get('coverage_status') == 'partial')


def secret(control, source):
    secret_id = 'dataSourceAPIkeys' if os.environ.get('CONSTELLATION_ROLE') == 'worker' else 'newKeys'
    try:
        response = control.session.client('secretsmanager').get_secret_value(SecretId=secret_id)
        credential = json.loads(response['SecretString'])[FIELDS[source]]
    except (ClientError, KeyError, ValueError):
        raise FeedError('credential_unavailable') from None
    if not isinstance(credential, str) or not credential.strip() or '\r' in credential or '\n' in credential:
        raise FeedError('credential_invalid')
    return credential.strip()


def fiscal_year(day):
    return day.year if day.month >= 4 else day.year - 1


def openalex_page(body, day, previous):
    obj = json.loads(body)
    items, meta = obj['results'], obj['meta']
    total, following = meta['count'], meta['next_cursor']
    if not isinstance(items, list) or type(total) is not int or total < len(items):
        raise FeedError('invalid_openalex_page_count')
    if len(items) > OPENALEX_PAGE_SIZE or (following is not None and (not isinstance(following, str) or not following)):
        raise FeedError('invalid_openalex_page_cursor')
    if not items and following is not None:
        raise FeedError('invalid_openalex_empty_page')
    if following == previous and following is not None:
        raise FeedError('openalex_cursor_did_not_advance')
    rows = []
    for work in items:
        identifier = work.get('id', '')
        if not OPENALEX_ID.fullmatch(identifier) or work.get('publication_date') != day:
            raise FeedError('openalex_work_outside_query')
        rows.append((identifier, day, work.get('updated_date'), identifier, work))
    return rows, following, total


def kaken_page(body, year, offset, active=False):
    if re.search(br'<!DOCTYPE|<!ENTITY', body, re.I):
        raise FeedError('unexpected_kaken_xml_declaration')
    root = ET.fromstring(body)
    if root.tag != 'grantAwards' or root.find('totalResults') is None:
        raise FeedError('invalid_kaken_response')
    total = int(root.findtext('totalResults'))
    start = int(root.findtext('startIndex'))
    per_page = int(root.findtext('itemsPerPage'))
    entries = root.findall('grantAward')
    if (start != offset or per_page not in (len(entries), KAKEN_PAGE_SIZE)
            or not 0 <= total <= 200000 or len(entries) > KAKEN_PAGE_SIZE
            or len(entries) != max(0, min(KAKEN_PAGE_SIZE, total - offset + 1))):
        raise FeedError('kaken_pagination_inconsistent')
    rows = []
    language = '{http://www.w3.org/XML/1998/namespace}lang'
    for entry in entries:
        identifier = entry.get('id', '')
        summaries = {node.get(language): node for node in entry.findall('summary')}
        award_periods = entry.findall('summary/periodOfAward')
        starts = {int(node.get('searchStartFiscalYear')) for node in award_periods
                  if node.get('searchStartFiscalYear')}
        periods = {(int(node.get('searchStartFiscalYear')), int(node.get('searchEndFiscalYear')))
                   for node in award_periods
                   if node.get('searchStartFiscalYear') and node.get('searchEndFiscalYear')}
        # A search by start year can be verified even when the project summary
        # leaves its end open. Later active years still need a bounded period.
        in_scope = year in starts or (active and any(start <= year <= end for start, end in periods))
        if not KAKEN_ID.fullmatch(identifier) or not in_scope:
            raise FeedError('kaken_project_outside_fiscal_scope')
        source_url = f'https://kaken.nii.ac.jp/grant/{identifier}/'
        # Keep the established projection for summaries with a complete period.
        period_start = min((start for start, _ in periods), default=min(starts))
        project = {
            'award_number': entry.get('awardNumber'),
            'project_type': entry.get('projectType'),
            'fiscal_start': period_start,
            'fiscal_end': max((end for _, end in periods), default=None),
            'created': entry.findtext('created'),
            'modified': entry.findtext('modified'),
            'titles': {lang: node.findtext('title') for lang, node in summaries.items() if lang},
        }
        rows.append((identifier, None, project['modified'], source_url, project))
    following = offset + len(rows)
    return rows, str(following) if following <= total else None, total


def fetch_page(session, source, scope, cursor, credential):
    headers = {'User-Agent': AGENT}
    if source == OPENALEX:
        day = scope['date']
        params = {'filter': f'from_publication_date:{day},to_publication_date:{day}',
                  'corpus': 'all', 'sort': 'publication_date:asc',
                  'per_page': OPENALEX_PAGE_SIZE, 'cursor': cursor or '*'}
        headers['Authorization'] = 'Bearer ' + credential
    else:
        year = scope['fiscal_year']
        params = {'s1': year, 's2': year, 'o1': 3 if scope['active'] else 1,
                  'st': int(cursor or 1), 'rw': KAKEN_PAGE_SIZE, 'lang': 'en',
                  'format': 'xml', 'appid': credential}
    try:
        with session.get(URLS[source], params=params, headers=headers, stream=True,
                         allow_redirects=False, timeout=(8, 35)) as response:
            if response.status_code in {429, 503}:
                raise Deferred(f'{source}_http_{response.status_code}')
            if response.status_code != 200:
                raise FeedError(f'{source}_http_{response.status_code}')
            body = bytearray()
            for data in response.iter_content(65536):
                body.extend(data)
                if len(body) > MAX_RESPONSE:
                    raise FeedError('provider_response_too_large')
    except requests.RequestException:
        raise FeedError('provider_connection_failed') from None
    body = bytes(body)
    if source == KAKEN and credential.encode() in body:
        raise FeedError('kaken_response_contains_credential')
    try:
        if source == OPENALEX:
            rows, following, total = openalex_page(body, day, cursor)
        else:
            rows, following, total = kaken_page(body, year, int(cursor or 1), scope['active'])
    except (ValueError, KeyError, TypeError, AttributeError, ET.ParseError):
        raise FeedError('provider_response_schema_changed') from None
    return body, rows, following, total


def compact_record(fields, mode, window, retrieved, raw_uri):
    identifier, event_date, modified, url, payload = fields
    return canonical({
        'source_record_id': identifier, 'event_date': event_date,
        'provider_updated_at': modified, 'source_url': url, 'raw_uri': raw_uri,
        'collected_at': retrieved, 'collection_mode': mode, 'window_id': window,
        'payload_json': canonical(payload).decode(),
    }) + b'\n'


def store_records(evidence, source, mode, namespace, lines):
    block = bytearray()
    uris = []
    for line in lines:
        if block and len(block) + len(line) > MAX_BATCH:
            uris.append(store_block(evidence, source, mode, namespace, block))
            block.clear()
        block.extend(line)
    if block:
        uris.append(store_block(evidence, source, mode, namespace, block))
    return uris


def store_block(evidence, source, mode, namespace, content):
    data = gzip.compress(content, compresslevel=3, mtime=0)
    key = f'records/{source}/{mode}/{namespace}/{hashlib.sha256(data).hexdigest()}.jsonl.gz'
    return evidence.immutable(key, data, 'application/gzip')['uri']


def read_index(evidence, uri, expected_sha):
    response = evidence.s3.get_object(Bucket=evidence.bucket, Key=uri.split('/', 3)[3])
    with response['Body'] as body:
        compressed = body.read()
    if hashlib.sha256(compressed).hexdigest() != expected_sha:
        raise FeedError('id_index_checksum_mismatch')
    return gzip.decompress(compressed).decode().splitlines()


def validate_window(evidence, batches, count, minimum, maximum):
    ids = set()
    for batch in batches:
        ids.update(read_index(evidence, batch['id_index']['uri'], batch['id_index']['sha256']))
    return len(ids), count == len(ids) == minimum == maximum


def api_window(evidence, source, mode, window, scope, credential, pages, session, reserve):
    key = f'checkpoints/{source}/{mode}/{window}.json'
    state, token = evidence.state(key)
    state = state or {'cursor': None, 'pages': 0, 'records': 0, 'batches': []}
    if state.get('scope', scope) != scope:
        raise FeedError('checkpoint_scope_mismatch')
    # A stopped writer may have committed a checkpoint before publishing its
    # batch. Published manifests are immutable and can be reconciled in place.
    published = state.get('published_batches', 0)
    for i, batch in enumerate(state['batches'][published:], start=published):
        evidence.publish(source, mode, f'{window}-{i:06d}', batch['records'])
    if published < len(state['batches']):
        state['published_batches'] = len(state['batches'])
        token = evidence.save(key, state, token)
    if state.get('exhausted'):
        return state

    for first_page in range(0, pages, BATCH_PAGES):
        spent = min(BATCH_PAGES, pages - first_page)
        if not reserve(spent):
            break
        cursor = state['cursor']
        count, lowest, highest = state['records'], state.get('total_min'), state.get('total_max')
        raw_files, ids, files = [], [], []
        block = bytearray()
        completed = 0
        error = None
        namespace = f'{window}-{len(state["batches"]):06d}'
        retrieved = datetime.now(timezone.utc).isoformat()
        while completed < spent:
            try:
                body, rows, following, total = fetch_page(session, source, scope, cursor, credential)
            except FeedError as failure:
                error = failure
                break
            fingerprint = hashlib.sha256(body).hexdigest()
            raw = evidence.immutable(f'raw/{source}/{fingerprint}.gz', gzip.compress(body, compresslevel=3, mtime=0),
                                     'application/gzip')
            raw_files.append(raw)
            for row in rows:
                line = compact_record(row, mode, window, retrieved, raw['uri'])
                if block and len(block) + len(line) > MAX_BATCH:
                    files.append(store_block(evidence, source, mode, namespace, block))
                    block.clear()
                block.extend(line)
            ids.extend(row[0] for row in rows)
            lowest = min(lowest, total) if lowest is not None else total
            highest = max(highest, total) if highest is not None else total
            count += len(rows)
            completed += 1
            if following is not None and following == cursor:
                raise FeedError('provider_cursor_did_not_advance')
            cursor = following
            if cursor is None:
                break
            if source == KAKEN:
                time.sleep(1)

        if completed:
            if block:
                files.append(store_block(evidence, source, mode, namespace, block))
            data = gzip.compress(''.join(identifier + '\n' for identifier in ids).encode(), mtime=0)
            id_index = evidence.immutable(
                f'identity/{source}/{hashlib.sha256(data).hexdigest()}.gz', data, 'application/gzip')
            batches = state['batches'] + [{'raw': raw_files, 'records': files, 'id_index': id_index}]
            updated = {'scope': scope, 'cursor': cursor, 'records': count, 'pages': state['pages'] + completed,
                       'batches': batches, 'published_batches': len(batches) - 1,
                       'total_min': lowest, 'total_max': highest, 'exhausted': cursor is None,
                       'updated_at': retrieved}
            if updated['exhausted']:
                unique, matched = validate_window(evidence, batches, count, lowest, highest)
                updated.update(unique_records=unique, coverage_status='complete' if matched else 'partial')
            token = evidence.save(key, updated, token)
            evidence.publish(source, mode, namespace, files)
            updated['published_batches'] = len(batches)
            token = evidence.save(key, updated, token)
            state = updated

        if error:
            raise error
        if state.get('exhausted'):
            break
    return state


def openalex_budget(evidence, stream, today, lane):
    key = f'quotas/{stream}/{today.isoformat()}-{lane}.json'

    def reserve(pages):
        state, token = evidence.state(key)
        used = (state or {}).get('used', 0)
        if used + pages > OPENALEX_LIMITS[lane]:
            return False
        evidence.save(key, {'used': used + pages}, token)
        return True

    return reserve


def run_openalex_api(evidence, today, pages, session, credential):
    results = {}
    lanes = [('daily', DAILY_ORIGIN, today - timedelta(days=1), pages),
             ('bridge', SNAPSHOT_DATE, DAILY_ORIGIN, max(BATCH_PAGES, pages // 4))]
    for lane, origin, stop, budget in lanes:
        key = f'progress/{OPENALEX}/{lane}.json'
        progress, token = evidence.state(key)
        day = date.fromisoformat(progress['next']) if progress else origin
        if day >= stop:
            continue
        try:
            state = api_window(evidence, OPENALEX, 'daily' if lane == 'daily' else 'historical',
                               day.isoformat(), {'date': day.isoformat()}, credential, budget, session,
                               openalex_budget(evidence, OPENALEX, today, lane))
        except Deferred as error:
            results[lane] = {'window': day.isoformat(), 'status': str(error)}
            continue
        results[lane] = api_summary(day.isoformat(), state)
        if state.get('exhausted'):
            evidence.save(key, {'next': (day + timedelta(days=1)).isoformat()}, token)
    return results


def api_summary(window, state):
    return {'window': window, 'records': state['records'], 'pages': state['pages'],
            'status': state.get('coverage_status', 'in_progress')}


def run_kaken(evidence, mode, today, pages, session, credential, allowed):
    fy = fiscal_year(today)
    key = f'progress/{KAKEN}/{mode}.json'
    progress, token = evidence.state(key)
    if mode == 'historical':
        position = int(progress['next']) if progress else FLOOR.year
        if position >= fy:
            return {'status': 'current', 'through_fiscal_year': position - 1}
        window, year, active = f'fy-{position}', position, False
        following = position + 1
    else:
        # Finish an interrupted daily snapshot before starting a new one.
        position = date.fromisoformat(progress['next']) if progress else today
        if position > today:
            return {'status': 'current', 'through': (position - timedelta(days=1)).isoformat()}
        if progress is None:
            token = evidence.save(key, {'next': position.isoformat()}, token)
        window, year, active = position.isoformat(), fiscal_year(position), True
        following = max(position + timedelta(days=1), today).isoformat()

    state = api_window(evidence, KAKEN, mode, window,
                       {'fiscal_year': year, 'active': active}, credential, pages, session, lambda _: allowed())
    if state.get('exhausted'):
        if mode == 'historical' and state.get('coverage_status') != 'complete':
            raise FeedError('kaken_historical_window_requires_reconciliation')
        evidence.save(key, {'next': following}, token)
    return api_summary(window, state)


def snapshot_manifest(public):
    response = public.get_object(Bucket=SNAPSHOT_BUCKET, Key=SNAPSHOT_KEY)
    with response['Body'] as stream:
        raw = stream.read(MAX_RESPONSE + 1)
    value = json.loads(raw)
    files = value['files']
    if (len(raw) > MAX_RESPONSE or value['date'] != SNAPSHOT_DATE.isoformat()
            or value['entity'] != 'works' or value['format'] != 'jsonl' or len(files) != SNAPSHOT_PARTS):
        raise FeedError('openalex_snapshot_release_changed')
    if len({entry['url'] for entry in files}) != len(files):
        raise FeedError('openalex_snapshot_duplicate_files')
    for entry in files:
        metadata = entry['meta']
        path = entry['url'].removeprefix('s3://openalex/')
        if (entry['url'] != 's3://openalex/' + path or not SNAPSHOT_FILE.fullmatch(path)
                or type(metadata['content_length']) is not int or metadata['content_length'] <= 0
                or type(metadata['record_count']) is not int or metadata['record_count'] <= 0):
            raise FeedError('invalid_openalex_snapshot_part')
    if (sum(entry['meta']['record_count'] for entry in files) != value['record_count']
            or sum(entry['meta']['content_length'] for entry in files) != value['content_length']):
        raise FeedError('invalid_openalex_snapshot_totals')
    return value, raw, response['ETag']


def snapshot_rows(stream, entry, count, collected_at):
    with gzip.GzipFile(fileobj=stream) as uncompressed:
        while line := uncompressed.readline(MAX_RESPONSE + 1):
            if len(line) > MAX_RESPONSE:
                raise FeedError('openalex_snapshot_record_too_large')
            work = json.loads(line)
            count['scanned'] += 1
            published = work.get('publication_date')
            if not published:
                count['undated'] += 1
                continue
            published = date.fromisoformat(published)
            if not FLOOR <= published <= SNAPSHOT_DATE:
                continue
            identifier = work['id']
            if not OPENALEX_ID.fullmatch(identifier):
                raise FeedError('invalid_openalex_snapshot_identity')
            count['retained'] += 1
            record = (identifier, published.isoformat(), work.get('updated_date'), identifier, work)
            yield compact_record(record, 'historical', SNAPSHOT_DATE.isoformat(), collected_at, entry['url'])


def run_snapshot(evidence, public, parts, live_allowed, canary=False, fence=lambda: None):
    manifest, raw, etag = snapshot_manifest(public)
    checksum = hashlib.sha256(raw).hexdigest()
    manifest_receipt = evidence.immutable(
        f'snapshots/{SNAPSHOT_DATE}/{checksum}.json', raw, 'application/json')
    key = f'progress/{OPENALEX}/snapshot.json'
    progress, token = evidence.state(key)
    files = manifest['files']
    start = 0
    if canary:
        candidates = [(entry['meta']['content_length'], index) for index, entry in enumerate(files)
                      if entry['url'].split('updated_date=')[-1][:10] >= '2025-01-01'
                      and entry['meta']['record_count'] >= 100]
        start = min(candidates)[1]
    progress = progress or {'next_part': start, 'snapshot_sha256': checksum, 'retained': 0, 'undated': 0}
    if progress['snapshot_sha256'] != checksum:
        raise FeedError('openalex_snapshot_manifest_changed')
    # A published receipt precedes progress advancement and can be replayed.
    stop = start + 1 if canary else len(files)
    for position in range(progress['next_part'], min(stop, progress['next_part'] + parts)):
        if not live_allowed():
            break
        fence()
        entry = files[position]
        part_key = f'snapshots/{SNAPSHOT_DATE}/parts/{position:06d}.json'
        receipt, part_token = evidence.state(part_key)
        if receipt is None:
            response = public.get_object(Bucket=SNAPSHOT_BUCKET, Key=entry['url'].removeprefix('s3://openalex/'))
            count = {'scanned': 0, 'retained': 0, 'undated': 0}
            try:
                with response['Body'] as stream:
                    if response['ContentLength'] != entry['meta']['content_length']:
                        raise FeedError('openalex_snapshot_part_size_changed')
                    # Stable throughout a replay of this release and part. This
                    # is the provider file time, with the capture in the receipt.
                    collected = response['LastModified'].isoformat()
                    uris = store_records(evidence, OPENALEX, 'historical', f'snapshot-{position:06d}',
                                        snapshot_rows(stream, entry, count, collected))
            except (OSError, TypeError, ValueError, KeyError, EOFError):
                raise FeedError('openalex_snapshot_part_unreadable') from None
            if count['scanned'] != entry['meta']['record_count']:
                raise FeedError('openalex_snapshot_part_count_mismatch')
            public.head_object(Bucket=SNAPSHOT_BUCKET, Key=SNAPSHOT_KEY, IfMatch=etag)
            fence()
            receipt = {**count, 'part': entry['url'], 'etag': response['ETag'],
                       'retrieved_at': datetime.now(timezone.utc).isoformat(),
                       'snapshot': manifest_receipt['uri'], 'records': uris}
            evidence.save(part_key, receipt, part_token)
        fence()
        evidence.publish(OPENALEX, 'historical', f'snapshot-{position:06d}', receipt['records'])
        progress = {'next_part': position + 1, 'snapshot_sha256': checksum,
                    'retained': progress['retained'] + receipt['retained'],
                    'undated': progress['undated'] + receipt['undated']}
        token = evidence.save(key, progress, token)
    if canary:
        return {'status': 'canary_verified', 'parts': progress['next_part'] - start,
                'retained': progress['retained']}
    return {'status': 'complete' if progress['next_part'] == len(files) else 'in_progress',
            'parts': progress['next_part'], 'total_parts': len(files),
            'retained': progress['retained'], 'snapshot': manifest_receipt['uri']}


def serialized_snapshot(evidence, public, parts, live_allowed):
    # Both workers use the same RDS server. Keep the advisory lock on its own
    # live connection across selection, provider download and commit.
    name = 'constellation:openalex:snapshot-writer'
    with evidence.control.db() as cursor:
        cursor.execute('SELECT GET_LOCK(%s,0) AS acquired', (name,))
        if cursor.fetchone()['acquired'] != 1:
            return {'status': 'deferred', 'reason': 'openalex_snapshot_other_writer'}

        def fence():
            cursor.execute('SELECT IS_USED_LOCK(%s)=CONNECTION_ID() AS owned', (name,))
            if cursor.fetchone()['owned'] != 1:
                raise FeedError('openalex_snapshot_writer_lock_lost')

        try:
            return run_snapshot(evidence, public, parts, live_allowed, fence=fence)
        finally:
            cursor.execute('SELECT RELEASE_LOCK(%s)', (name,))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', choices=sorted(URLS))
    parser.add_argument('mode', choices=('daily', 'historical'))
    parser.add_argument('--budget', type=int, default=20, help='Maximum API pages or snapshot parts per run')
    parser.add_argument('--canary', action='store_true', help='Use an isolated S3 prefix and one page or part')
    args = parser.parse_args()
    if not 1 <= args.budget <= 500:
        parser.error('budget must be between 1 and 500')
    control = Control()
    def allowed():
        if args.mode == 'daily':
            return control.daily_allowed()
        if Path('/opt/constellation/trial-historical-policy.json').is_file():
            from constellation.trial_historical_access import allowed as trial_allowed
            return not BATCH_PAUSE.exists() and trial_allowed(control, args.source)
        return not BATCH_PAUSE.exists() and control.allowed()

    if not args.canary and not allowed():
        print(json.dumps({'source': args.source, 'mode': args.mode, 'status': 'paused'}))
        return 0
    evidence = Evidence(control)
    budget = args.budget
    if args.canary:
        evidence.prefix += '/canary-v2'
        budget = 1
    now = datetime.now(timezone.utc)
    try:
        if args.source == OPENALEX and args.mode == 'historical':
            public = boto3.client('s3', region_name='us-east-1', config=Config(signature_version=UNSIGNED))
            result = (run_snapshot(evidence, public, budget, lambda: True, canary=True) if args.canary
                      else serialized_snapshot(evidence, public, budget, allowed))
        else:
            with requests.Session() as session:
                credential = secret(control, args.source)
                if args.source == KAKEN:
                    result = run_kaken(evidence, args.mode, now.astimezone(JAPAN).date(), budget, session,
                                       credential, (lambda: True) if args.canary else allowed)
                elif args.canary:
                    day = (now.date() - timedelta(days=2)).isoformat()
                    result = api_summary(day, api_window(evidence, OPENALEX, 'daily', day, {'date': day},
                                                          credential, 2, session, lambda _: True))
                else:
                    result = run_openalex_api(evidence, now.date(), budget, session, credential)
    except Deferred as error:
        result = {'status': 'deferred', 'reason': str(error)}
    except Exception as error:
        # Never emit exception messages that may contain signed URLs or appid.
        code = error.response['Error'].get('Code') if isinstance(error, ClientError) else None
        result = {'status': 'failed', 'reason': str(error) if isinstance(error, FeedError) else type(error).__name__}
        if code:
            result['aws_code'] = code
        print(json.dumps({'source': args.source, 'mode': args.mode, **result}), flush=True)
        return 1
    print(json.dumps({'source': args.source, 'mode': args.mode, **result}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
