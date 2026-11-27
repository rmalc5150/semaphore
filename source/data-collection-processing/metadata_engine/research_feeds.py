"""Discover committed research feed batches and verify their provider evidence."""

from datetime import date
from functools import lru_cache
import gzip
import hashlib
import io
import json
import re
from xml.etree import ElementTree as ET

from metadata_engine.evidence import RawFailure, Uncommitted, object_bytes

OPENALEX = 'openalex_scholarly_graph'
KAKEN = 'japan_kaken_funded_research'
DATASETS = {OPENALEX: 'works_metadata', KAKEN: 'grant_projects'}
KINDS = {OPENALEX: 'openalex_work_metadata', KAKEN: 'kaken_project_xml'}
PREFIX = 'research-data/constellation-backfill/research-feeds/v1'
FORM = 'research_feed'
MAX_EXPANDED = 64 * 1024**2
WORK_ID = re.compile(r'https://openalex\.org/W[1-9]\d*')
PROJECT_ID = re.compile(r'KAKENHI-[A-Z]+-[A-Za-z0-9-]+')
SHA = r'[0-9a-f]{64}'
NAMESPACE = r'(?:\d{4}-\d{2}-\d{2}|fy-\d{4})-\d{6}|snapshot-\d{6}'
SNAPSHOT_DATE = '2026-10-14'


def locator(key, source, mode):
    match = re.fullmatch(rf'{PREFIX}/records/{source}/{mode}/({NAMESPACE})/({SHA})\.jsonl\.gz', key)
    if not match or (match[1].startswith('snapshot-') and (source != OPENALEX or mode != 'historical')):
        raise RawFailure('invalid_research_feed_batch_location')
    return match.groups()


def manifest_entries(s3, bucket, key, source, mode):
    namespace = key.rsplit('/', 1)[1].removesuffix('.manifest')
    if not re.fullmatch(rf'{PREFIX}/published/{source}/{mode}/({NAMESPACE})\.manifest', key):
        raise RawFailure('invalid_research_feed_manifest_location')
    raw = object_bytes(s3, bucket, key, 1024 * 1024)
    entries = []
    for uri in raw.decode('ascii').splitlines():
        if not uri.startswith(f's3://{bucket}/'):
            raise RawFailure('research_feed_manifest_bucket_mismatch')
        batch = uri.removeprefix(f's3://{bucket}/')
        found, checksum = locator(batch, source, mode)
        if found != namespace:
            raise RawFailure('research_feed_manifest_batch_mismatch')
        entries.append((batch, checksum))
    if not entries or len(set(entries)) != len(entries):
        raise RawFailure('empty_or_duplicate_research_feed_manifest')
    return entries


def discover(db, s3, pagesize=24, *, include_daily=True):
    """Queue only published artifacts and periodically revisit earlier prefixes."""
    counts = {}
    s3_bucket = db.config['bucket']
    for source in DATASETS:
        policy = db.config['contracts'].get(source, {})
        if policy.get('adapter') != FORM or policy.get('state') != 'enabled':
            continue
        with db.tx() as tx:
            tx.execute('SELECT contract_version,state FROM engine_sources WHERE source_key=%s', (source,))
            live = tx.fetchone()
        if not live or live['state'] != 'enabled' or live['contract_version'] != policy['contract_version']:
            continue
        for mode in ('daily', 'historical'):
            if mode == 'daily' and not include_daily:
                continue
            prefix = f'{PREFIX}/published/{source}/{mode}/'
            cursor_id = f'research-feeds:{source}:{mode}'
            cursor = db.cursor(cursor_id)
            options = {'Bucket': s3_bucket, 'Prefix': prefix, 'MaxKeys': pagesize}
            if cursor.get('after'):
                options['StartAfter'] = cursor['after']
            page = s3.list_objects_v2(**options)
            entries = page.get('Contents', [])
            batches = [entry for item in entries
                       for entry in manifest_entries(s3, s3_bucket, item['Key'], source, mode)]
            added = 0
            # Keep transactions short enough for the shared queue database.
            for offset in range(0, len(batches), 64):
                with db.tx() as tx:
                    for key, checksum in batches[offset:offset + 64]:
                        added += int(db.enqueue(source, key, checksum, FORM, 20, tx))
            db.save_cursor(cursor_id, {'after': entries[-1]['Key'] if entries and page.get('IsTruncated') else None})
            counts[f'{source}:{mode}'] = added
    return counts


def expanded(data):
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
            body = stream.read(MAX_EXPANDED + 1)
    except (OSError, EOFError) as error:
        raise RawFailure('invalid_research_feed_gzip') from error
    if not body or len(body) > MAX_EXPANDED:
        raise RawFailure('research_feed_gzip_size')
    return body


@lru_cache(maxsize=8)
def _snapshot_manifest_entries(s3, bucket, manifest):
    # Snapshot commit manifests use conditional, immutable writes. Daily and
    # API historical manifests continue to be checked live for each batch.
    return frozenset(manifest_entries(s3, bucket, manifest, OPENALEX, 'historical'))


@lru_cache(maxsize=8)
def _snapshot_part_receipt(s3, bucket, namespace):
    number = namespace.removeprefix('snapshot-')
    receipt_key = f'{PREFIX}/snapshots/{SNAPSHOT_DATE}/parts/{number}.json'
    receipt = json.loads(object_bytes(s3, bucket, receipt_key))
    if not re.fullmatch(
            r's3://openalex/data/jsonl/works/updated_date=\d{4}-\d{2}-\d{2}/part_\d+\.gz', receipt['part']):
        raise RawFailure('openalex_snapshot_receipt_mismatch')
    if not re.fullmatch(rf's3://{re.escape(bucket)}/{PREFIX}/snapshots/{SNAPSHOT_DATE}/{SHA}\.json',
                        receipt['snapshot']):
        raise RawFailure('openalex_snapshot_manifest_identity')
    return receipt


def snapshot_receipt(s3, bucket, namespace, key):
    # Snapshot collection creates the receipt once and publishes only after
    # that succeeds. Check membership for every batch, even on a cache hit.
    receipt = _snapshot_part_receipt(s3, bucket, namespace)
    if f's3://{bucket}/{key}' not in receipt['records']:
        raise RawFailure('openalex_snapshot_receipt_mismatch')
    return {**receipt, 'records': list(receipt['records'])}


def load_batch(s3, bucket, job):
    key, source = job['input_key'], job['source_key']
    mode = key.split('/')[-3]
    if source not in DATASETS or mode not in {'daily', 'historical'}:
        raise RawFailure('unknown_research_feed_source_or_mode')
    namespace, checksum = locator(key, source, mode)
    manifest = f'{PREFIX}/published/{source}/{mode}/{namespace}.manifest'
    is_snapshot = namespace.startswith('snapshot-')
    entries = (_snapshot_manifest_entries(s3, bucket, manifest) if is_snapshot
               else manifest_entries(s3, bucket, manifest, source, mode))
    if (key, checksum) not in entries:
        raise Uncommitted('research_feed_batch_not_published')
    raw = object_bytes(s3, bucket, key, expected=checksum)
    receipt = snapshot_receipt(s3, bucket, namespace, key) if is_snapshot else None
    rows = []
    for line in expanded(raw).splitlines():
        saved = json.loads(line)
        if saved['collection_mode'] != mode:
            raise RawFailure('research_feed_mode_mismatch')
        identifier = saved['source_record_id']
        data = json.loads(saved['payload_json'])
        when = saved.get('event_date')
        if source == OPENALEX:
            if (not WORK_ID.fullmatch(identifier) or saved['source_url'] != identifier
                    or data.get('id') != identifier or data.get('publication_date') != when
                    or not isinstance(data.get('authorships'), list) or not isinstance(data.get('ids'), dict)
                    or not isinstance(data.get('type'), str)):
                raise RawFailure('invalid_openalex_works_record')
            if not when or date.fromisoformat(when).isoformat() != when:
                raise RawFailure('invalid_openalex_publication_date')
        elif (not PROJECT_ID.fullmatch(identifier) or when is not None
              or saved['source_url'] != f'https://kaken.nii.ac.jp/grant/{identifier}/'):
            raise RawFailure('invalid_kaken_grant_record')
        if receipt:
            if (saved['raw_uri'] != receipt['part'] or saved['window_id'] != SNAPSHOT_DATE
                    or not '2016-01-01' <= when <= SNAPSHOT_DATE):
                raise RawFailure('openalex_snapshot_row_mismatch')
            collected = receipt.get('retrieved_at') or saved['collected_at']
        else:
            if saved['window_id'] != namespace.rsplit('-', 1)[0] or (source == OPENALEX and when != saved['window_id']):
                raise RawFailure('research_feed_window_mismatch')
            collected = saved['collected_at']
        rows.append({
            'source': source, 'dataset': DATASETS[source], 'source_record_id': identifier,
            'source_url': saved['source_url'], 'ingested_at': collected,
            'parser_version': 'research-feeds-v1',
            'event_at': {'value': when, 'precision': 'day'} if when else None,
            'available_at': None, 'availability_basis': 'historical_version_availability_unverified',
            'payload': {'data': data, 'collection_mode': mode, 'window_id': saved['window_id'],
                        'provider_updated_at': saved.get('provider_updated_at')},
            '_research_evidence': {'batch_key': key, 'batch_checksum': checksum, 'batch_bytes': len(raw),
                                   'raw_uri': saved['raw_uri'], 'snapshot': receipt},
        })
    return rows, raw, {'task': {'mode': mode}, 'status': 'committed_batch'}


@lru_cache(maxsize=2)
def provider_page(s3, bucket, key, expected, source):
    compressed = object_bytes(s3, bucket, key)
    body = expanded(compressed)
    if hashlib.sha256(body).hexdigest() != expected:
        raise RawFailure('research_feed_provider_page_checksum')
    if source == OPENALEX:
        items = json.loads(body).get('results')
        if not isinstance(items, list):
            raise RawFailure('invalid_openalex_results')
        indexed = {item['id']: item for item in items}
    else:
        if re.search(br'<!DOCTYPE|<!ENTITY', body, re.I):
            raise RawFailure('unexpected_kaken_xml_declaration')
        try:
            content = ET.fromstring(body)
        except ET.ParseError as error:
            raise RawFailure('invalid_kaken_project_xml') from error
        if content.tag != 'grantAwards' or content.find('totalResults') is None:
            raise RawFailure('invalid_kaken_project_xml')
        items = content.findall('grantAward')
        indexed = {item.get('id'): item for item in items}
    if len(indexed) != len(items):
        raise RawFailure('research_feed_provider_duplicate_id')
    return indexed, hashlib.sha256(compressed).hexdigest(), len(compressed)


def kaken_projection(project):
    language = '{http://www.w3.org/XML/1998/namespace}lang'
    award_periods = project.findall('summary/periodOfAward')
    starts = [int(node.get('searchStartFiscalYear')) for node in award_periods
              if node.get('searchStartFiscalYear')]
    if not starts:
        raise RawFailure('kaken_project_fiscal_period_missing')
    periods = [(int(node.get('searchStartFiscalYear')), int(node.get('searchEndFiscalYear')))
               for node in award_periods
               if node.get('searchStartFiscalYear') and node.get('searchEndFiscalYear')]
    titles = {node.get(language): node.findtext('title') for node in project.findall('summary') if node.get(language)}
    return {'award_number': project.get('awardNumber'), 'project_type': project.get('projectType'),
            'fiscal_start': min((start for start, _ in periods), default=min(starts)),
            'fiscal_end': max((end for _, end in periods), default=None),
            'created': project.findtext('created'), 'modified': project.findtext('modified'), 'titles': titles}


def evidence(record, s3, bucket):
    ref = record.get('_research_evidence')
    if not ref:
        raise RawFailure('committed_research_feed_evidence_required')
    source = record['source']
    if ref['snapshot']:
        receipt = ref['snapshot']
        return [{
            'artifact_kind': KINDS[source], 's3_uri': f's3://{bucket}/{ref["batch_key"]}',
            'sha256': ref['batch_checksum'], 'bytes': ref['batch_bytes'],
            'origin': 'first_party_source', 'source_url': record['source_url'],
            'upstream_uri': receipt['part'], 'snapshot_manifest': receipt['snapshot'],
            'validation': 'complete provider work object in verified snapshot batch',
        }]
    match = re.fullmatch(rf's3://{re.escape(bucket)}/({PREFIX}/raw/{source}/({SHA})\.gz)', ref['raw_uri'])
    if not match:
        raise RawFailure('research_feed_provider_page_location')
    key, checksum = match.groups()
    indexed, compressed_sha, size = provider_page(s3, bucket, key, checksum, source)
    original = indexed.get(record['source_record_id'])
    if original is None:
        raise RawFailure('research_feed_record_missing_from_provider_page')
    data = original if source == OPENALEX else kaken_projection(original)
    if data != record['payload']['data']:
        raise RawFailure('research_feed_provider_record_mismatch')
    endpoint = 'https://api.openalex.org/works' if source == OPENALEX else 'https://kaken.nii.ac.jp/opensearch/'
    return [{
        'artifact_kind': KINDS[source], 's3_uri': ref['raw_uri'], 'sha256': compressed_sha,
        'bytes': size, 'origin': 'first_party_source', 'source_url': endpoint,
        'provider_content_sha256': checksum, 'retrieved_at': record['ingested_at'],
        'validation': 'matched exact original provider project XML' if source == KAKEN else 'matched complete work object',
    }]
