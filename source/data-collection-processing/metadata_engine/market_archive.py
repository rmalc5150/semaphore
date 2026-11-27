"""Label verified, manually retained market-workbook release files."""
import csv
from datetime import date
import hashlib
import io
import json
import re
import tempfile
from urllib.parse import urlsplit
from zipfile import BadZipFile, ZipFile

from market_source_capture import MARKET, json_bytes, immutable_put
from metadata_engine.evidence import RawFailure, object_bytes, s3_key

VERSION = '2.0.3-market-archive-v1'
ADAPTER = 'market_archive_original'
TRENDS = 'market_source_166'
VAERS = 'market_source_248'
RECEIPTS = MARKET + '/metadata-receipts/'
VAERS_TABLES = {'DATA': ('reports', 'RECVDATE'), 'SYMPTOMS': ('symptoms', 'SYMPTOM1'),
                'VAX': ('vaccines', 'VAX_TYPE')}


def contracts():
    profiles = {
        TRENDS: (166, 'provider_data', 'trends.google.com',
                 'One original Explore CSV on its own normalization scale and observation window.'),
        VAERS: (248, 'annual_packages', 'vaers.hhs.gov',
                'One original annual ZIP with its native report, symptom and vaccine tables.'),
    }
    return {
        source: {'source_key': source, 'catalog_entries': [entry], 'datasets': [dataset],
                 'state': 'enabled', 'contract_version': VERSION, 'adapter': ADAPTER,
                 'adapter_version': VERSION, 'record_kind': 'provider_release_file',
                 'license_policy_id': 'source-rights-review-required', 'allowed_hosts': [host],
                 'completeness_scope': scope,
                 'raw_requirements': {'version': VERSION, 'minimum_completeness': 'complete',
                                      'required_artifact_kinds': ['dataset_file'],
                                      'forbidden_shortcuts': ['discovery_page', 'unchecked_original']}}
        for source, (entry, dataset, host, scope) in profiles.items()
    }


def trends_rows(stream, term, first_year, last_year):
    start, stop = date(first_year, 1, 1), date(last_year + 1, 1, 1)
    rows = csv.reader(stream)
    if next(rows, None) != ['Category: All categories']:
        raise ValueError('unexpected_trends_category')
    header = next((row for row in rows if row), None)
    if header != ['Week', f'{term}: (Worldwide)']:
        raise ValueError('unexpected_trends_timeline_header')
    previous = first_week = last_week = None
    for row in rows:
        if not row:
            continue
        if len(row) != 2 or not re.fullmatch(r'\d{4}-\d\d-\d\d', row[0]):
            raise ValueError('invalid_trends_week')
        day, interest = date.fromisoformat(row[0]), row[1]
        if day.weekday() != 6 or (previous and (day - previous).days != 7):
            raise ValueError('non_contiguous_trends_weeks')
        if not (interest == '<1' or re.fullmatch(r'100|[1-9]?\d', interest)):
            raise ValueError('invalid_trends_interest')
        previous = day
        if start <= day < stop:
            first_week = first_week or day
            last_week = day
            yield rows.line_num, day.isoformat(), interest
    if not first_week or (first_week - start).days >= 7 or (stop - last_week).days > 7:
        raise ValueError('incomplete_trends_window')


def trends_receipt(spec, result):
    refs = result['raw']
    if result['source'] != TRENDS or result['dataset'] != 'provider_data' or result['bounded_parse']:
        raise ValueError('unexpected_trends_archive_result')
    return {
        'source': TRENDS, 'dataset': 'provider_data', 'market_archive_original': True,
        'mode': 'historical', 'source_url': refs['source_url'], 'artifact_uri': refs['s3_uri'],
        'sha256': refs['sha256'], 'bytes': refs['bytes'], 'retrieved_at': refs['retrieved_at'],
        'scope': {'term': spec['term'], 'first_year': spec['year'],
                  'last_year': spec.get('end_year', spec['year']), 'rows': result['records'],
                  'collection_manifest': result['manifest']},
    }


def vaers_receipt(archive, members, manifest_uri):
    year = int(re.fullmatch(r'(20\d{2})VAERSData\.zip', archive['file'])[1])
    return {
        'source': VAERS, 'dataset': 'annual_packages', 'market_archive_original': True,
        'mode': 'historical', 'source_url': archive['source_url'], 'artifact_uri': archive['archive_uri'],
        'sha256': archive['sha256'], 'bytes': archive['bytes'], 'retrieved_at': archive['retained_at'],
        'scope': {'year': year, 'release_manifest': manifest_uri,
                  'members': {item['member']: item['rows'] for item in members}},
    }


def retain_receipt(s3, bucket, receipt):
    key = f"{RECEIPTS}{receipt['source']}/{receipt['sha256']}.jsonl"
    body = json_bytes(receipt)
    try:
        immutable_put(s3, bucket, key, body, hashlib.sha256(body).hexdigest(), 'application/x-ndjson')
    except ValueError as error:
        if str(error) != 'retained_original_checksum_mismatch':
            raise
        existing = object_bytes(s3, bucket, key, 64 * 1024)
        original = json.loads(existing)
        if {**receipt, 'retrieved_at': original.get('retrieved_at')} != original:
            raise ValueError('conflicting_market_archive_receipt') from error
    return key


def from_receipt(receipt, input_key):
    source, sha = receipt['source'], receipt['sha256']
    if source not in (TRENDS, VAERS) or not re.fullmatch(r'[0-9a-f]{64}', sha):
        raise RawFailure('invalid_market_archive_identity')
    if input_key != f'{RECEIPTS}{source}/{sha}.jsonl':
        raise RawFailure('market_archive_receipt_key_mismatch')
    return {
        'source': source, 'dataset': receipt['dataset'], 'source_record_id': sha,
        'source_record_id_basis': 'provider_content_sha256',
        'source_url': receipt['source_url'], 'ingested_at': receipt['retrieved_at'],
        'available_at': None, 'parser_version': VERSION,
        'payload': {'data': receipt['scope'], 'source_evidence': [{
            's3_uri': receipt['artifact_uri'], 'sha256': sha, 'size': receipt['bytes'],
            'source_url': receipt['source_url'],
        }]},
    }


def read_vaers(s3, bucket, key, size, sha, year):
    if size > 256 * 1024**2:
        raise RawFailure('vaers_archive_too_large')
    response = s3.get_object(Bucket=bucket, Key=key)
    stream = response['Body']
    checksum = hashlib.sha256()
    length = 0
    try:
        with tempfile.TemporaryFile() as raw:
            for chunk in stream.iter_chunks(1024 * 1024):
                length += len(chunk)
                if length > size:
                    raise RawFailure('vaers_archive_length_mismatch')
                raw.write(chunk)
                checksum.update(chunk)
            if length != size or checksum.hexdigest() != sha:
                raise RawFailure('vaers_archive_checksum_or_length_mismatch')
            try:
                with ZipFile(raw) as archive:
                    expected = {f'{year}VAERS{suffix}.csv': info for suffix, info in VAERS_TABLES.items()}
                    if len(archive.infolist()) != len(expected) or set(archive.namelist()) != set(expected):
                        raise RawFailure('vaers_native_members_mismatch')
                    result = {}
                    for member, (table, signature) in expected.items():
                        with archive.open(member) as file:
                            header = file.readline(4096).decode('ascii').rstrip('\r\n').split(',')
                            if not header or header[0] != 'VAERS_ID' or signature not in header:
                                raise RawFailure('vaers_native_member_header_mismatch')
                            result[member] = table
                    return result
            except (BadZipFile, EOFError, UnicodeError) as exc:
                raise RawFailure('invalid_vaers_zip') from exc
    finally:
        stream.close()


def evidence(record, contract, s3, bucket):
    source, dataset = record['source'], record['dataset']
    ref, = record['payload']['source_evidence']
    scope = record['payload']['data']
    key, sha, size = s3_key(ref['s3_uri'], bucket), ref['sha256'], ref['size']
    url = urlsplit(ref['source_url'])
    if (source != contract['source_key'] or dataset not in contract['datasets'] or url.scheme != 'https'
            or url.hostname not in contract['allowed_hosts'] or type(size) is not int or size <= 0):
        raise RawFailure('market_archive_scope_mismatch')
    base = f'{MARKET}/historical-exports/{source}/'
    if source == TRENDS:
        first, last = scope['first_year'], scope['last_year']
        period = str(first) if first == last else f'{first}-{last}'
        if key != f'{base}provider_data/{period}/{sha}' or size > 1024 * 1024:
            raise RawFailure('trends_original_scope_mismatch')
        raw = object_bytes(s3, bucket, key, 1024 * 1024, sha)
        if len(raw) != size:
            raise RawFailure('trends_archive_length_mismatch')
        try:
            with io.StringIO(raw.decode('utf-8-sig')) as stream:
                rows = list(trends_rows(stream, scope['term'], first, last))
        except (ValueError, UnicodeError) as exc:
            raise RawFailure('invalid_trends_timeline') from exc
        if len(rows) != scope['rows']:
            raise RawFailure('trends_week_count_mismatch')
        record['payload']['data'] = {**scope, 'first_observation': rows[0][1],
                                    'last_observation': rows[-1][1], 'geography': 'Worldwide',
                                    'category': 'All categories', 'normalization': '0–100 per export'}
        media = 'text/csv'
    elif source == VAERS:
        year = scope['year']
        if key != f'{base}archives/{year}/{sha}':
            raise RawFailure('vaers_original_scope_mismatch')
        member_tables = read_vaers(s3, bucket, key, size, sha, year)
        if (set(member_tables) != set(scope['members'])
                or not all(type(count) is int and count > 0 for count in scope['members'].values())):
            raise RawFailure('vaers_member_count_scope_mismatch')
        record['payload']['data'] = {
            **scope, 'member_tables': member_tables, 'join_key': 'VAERS_ID',
        }
        media = 'application/zip'
    else:
        raise RawFailure('unsupported_market_archive_source')
    return [{'artifact_kind': 'dataset_file', 'origin': 'first_party_source',
             's3_uri': ref['s3_uri'], 'sha256': sha, 'bytes': size, 'media_type': media,
             'source_url': ref['source_url']}]
