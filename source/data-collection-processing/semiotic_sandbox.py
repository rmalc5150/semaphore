"""Deterministic evidence graph pilot. Offline by default; AWS is opt-in.

Input: frozen rows from the published metadata source_observations table.
Output: immutable JSON/Parquet graph release and Athena publication plan.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import time

VERSION = 'semiotic-sandbox-0.2'
MAX_CAPTURE_ROWS = 1000
MAX_CAPTURE_BYTES = 32 * 1024 * 1024
ROW_GROUP_ROWS = 512


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def sha(body):
    return hashlib.sha256(body).hexdigest()


def identity(kind, value):
    return kind + '_' + sha(encoded(value))


def query(client, sql, workgroup, *, max_rows=None, max_bytes=None):
    qid = client.start_query_execution(QueryString=sql, WorkGroup=workgroup,
        ResultReuseConfiguration={'ResultReuseByAgeConfiguration': {'Enabled': False}})['QueryExecutionId']
    deadline = time.monotonic() + 120
    while True:
        result = client.get_query_execution(QueryExecutionId=qid)['QueryExecution']
        state = result['Status']['State']
        if state == 'SUCCEEDED':
            rows, size, skip_header = [], 0, True
            for page in client.get_paginator('get_query_results').paginate(
                    QueryExecutionId=qid, PaginationConfig={'PageSize': 100 if max_bytes else 1000}):
                for row in page['ResultSet']['Rows']:
                    if skip_header:
                        skip_header = False
                        continue
                    values = [v.get('VarCharValue') for v in row['Data']]
                    if max_rows is not None and len(rows) >= max_rows:
                        raise ValueError(f'Athena capture exceeds {max_rows} rows; use fewer jobs')
                    if max_bytes is not None:
                        size += sum(len(v.encode('utf-8')) for v in values if v is not None)
                        if size > max_bytes:
                            raise ValueError(f'Athena capture exceeds {max_bytes} bytes; use fewer jobs')
                    rows.append(values)
            return qid, rows
        if state in ('FAILED', 'CANCELLED'):
            raise RuntimeError(result['Status'])
        if time.monotonic() > deadline:
            client.stop_query_execution(QueryExecutionId=qid)
            raise TimeoutError(qid)
        time.sleep(1)


def capture(client, jobs, workgroup):
    """Read explicit public partitions. No date watermark that could miss late jobs."""
    if not jobs or len(jobs) > 5 or any(not re.fullmatch('[a-f0-9]{64}', j) for j in jobs):
        raise ValueError('Supply one to five exact metadata job IDs')
    values = ','.join("'" + j + "'" for j in sorted(set(jobs)))
    qid, rows = query(client, 'SELECT job_id, labelled_json FROM '
        'optima_metadata_engine.source_observations WHERE job_id IN (' + values +
        f') LIMIT {MAX_CAPTURE_ROWS + 1}', workgroup,
        max_rows=MAX_CAPTURE_ROWS, max_bytes=MAX_CAPTURE_BYTES)
    if {r[0] for r in rows} != set(jobs):
        raise ValueError('Requested published jobs missing or empty')
    rows.sort(key=lambda row: (row[0], row[1]))
    observations = [json.loads(row[1]) for row in rows]
    return {'environment': 'sandbox', 'query_id': qid, 'jobs': sorted(set(jobs)),
            'observations': observations, 'observations_sha256': sha(encoded(observations))}


def normalize(namespace, value):
    value = str(value).strip()
    if namespace == 'CIK':
        if not re.fullmatch('[0-9]{1,10}', value) or int(value) == 0:
            raise ValueError('invalid CIK')
        return value.zfill(10)
    if namespace == 'NCT':
        value = value.upper()
        if not re.fullmatch('NCT[0-9]{8}', value):
            raise ValueError('invalid NCT')
        return value
    if namespace == 'DOI':
        value = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', value, flags=re.I).lower()
        if not re.fullmatch(r'10\.[0-9]{4,9}/\S+', value):
            raise ValueError('invalid DOI')
        return value
    raise ValueError('unsupported namespace')


PATTERNS = [('CIK', re.compile(r'\bCIK\s*[:#]?\s*([0-9]{1,10})\b', re.I)),
            ('NCT', re.compile(r'\b(NCT[0-9]{8})\b', re.I)),
            ('DOI', re.compile(r'\b(10\.[0-9]{4,9}/[^\s<>"\x27]+)', re.I))]


def evidence_pages(observation):
    return observation.get('extracted_pages', observation['payload'].get('pages', []))


def build(snapshot, registry, chunk_size=800):
    if snapshot.get('environment') != 'sandbox' or sha(encoded(snapshot['observations'])) != snapshot['observations_sha256']:
        raise ValueError('input snapshot identity mismatch')
    if chunk_size < 32:
        raise ValueError('chunk size too small')
    entity_rows = {e['entity_id']: e for e in registry.get('entities', [])}
    if registry.get('schema_version') == 1:
        from semiotic_registry import validate
        validate(registry)
    lookup = {}
    provisional = {}
    for item in registry['identifiers']:
        if item['review_status'] != 'verified':
            if item['review_status'] == 'candidate':
                key = (item['namespace'], normalize(item['namespace'], item['value']))
                provisional.setdefault(key, set()).add(item['entity_id'])
            continue
        key = (item['namespace'], normalize(item['namespace'], item['value']))
        lookup.setdefault(key, set()).add(item['entity_id'])
    tables = {k: [] for k in ('observations', 'chunks', 'mentions', 'bindings', 'edges', 'entities')}
    tables['entities'] = [dict(e, id=e['entity_id']) for e in entity_rows.values()]
    seen = {}
    for row in snapshot['observations']:
        obs = row['observation_id']
        if obs in seen:
            if seen[obs] != row:
                raise ValueError('conflicting observation ID')
            continue
        seen[obs] = row
        if row['quality_status'] != 'accepted' or row['raw_completeness_status'] != 'complete':
            raise ValueError('unaccepted observation')
        tables['observations'].append({'id': obs, 'record_id': row['record_id'],
            'raw_s3_uri': row['raw_s3_uri'], 'raw_sha256': row['raw_sha256'],
            'available_at': row.get('available_at'), 'ingested_at': row['ingested_at']})
        # Explicit adapter contract: pages contain extracted plain text. Never
        # recursively search arbitrary payload strings or invent PDF coordinates.
        pages = evidence_pages(row)
        for page in pages:
            text = page['text']
            for start in range(0, len(text), chunk_size):
                end = min(start + chunk_size, len(text))
                cid = identity('chunk', [VERSION, obs, page['page'], start, end, text[start:end]])
                tables['chunks'].append({'id': cid, 'observation_id': obs, 'page': page['page'],
                    'start': start, 'end': end, 'text': text[start:end],
                    'coordinate_system': 'unicode_codepoints_in_extracted_page'})
            # Scan complete page so identifiers crossing chunk boundaries survive.
            for namespace, pattern in PATTERNS:
                for match in pattern.finditer(text):
                    value = normalize(namespace, match.group(1))
                    start, end = match.span(1)
                    mid = identity('mention', [obs, page['page'], start, end, namespace, value])
                    tables['mentions'].append({'id': mid, 'observation_id': obs, 'namespace': namespace,
                        'value': value, 'page': page['page'], 'start': start, 'end': end,
                        'quote': text[start:end]})
                    verified = lookup.get((namespace, value), set())
                    pending = provisional.get((namespace, value), set())
                    candidates = sorted(verified | pending)
                    # Registry v1 is current-only. Do not claim historical binding.
                    status = ('ambiguous' if len(candidates) > 1 else 'matched_current' if verified
                              else 'provisional' if pending else 'unresolved')
                    binding = {'id': identity('binding', [mid, registry, candidates]), 'mention_id': mid,
                        'entity_id': candidates[0] if status == 'matched_current' else None,
                        'candidates': candidates, 'status': status, 'historically_eligible': False}
                    tables['bindings'].append(binding)
                    if binding['entity_id']:
                        tables['edges'].append({'id': identity('edge', [mid, binding['id']]),
                            'subject_id': obs, 'predicate': 'mentions_identifier_of',
                            'object_id': binding['entity_id'], 'evidence_id': mid,
                            'binding_id': binding['id'], 'historically_eligible': False})
    for rows in tables.values():
        rows.sort(key=lambda r: r['id'])
    release = {'version': VERSION, 'environment': 'sandbox', 'registry_sha256': sha(encoded(registry)),
        'input_sha256': sha(encoded({k: v for k, v in snapshot.items() if k != 'query_id'})),
        'chunk_size': chunk_size, 'tables': tables}
    release['release_id'] = identity('release', release)
    return release


def write_release(release, output):
    import pyarrow as pa
    import pyarrow.parquet as pq
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    root = output / release['release_id']
    body = encoded(release)
    def verify_existing():
        if (root / 'graph.json').read_bytes() != body:
            raise ValueError('immutable release conflict')
        manifest = json.loads((root / 'manifest.json').read_bytes())
        expected = {name: len(rows) for name, rows in release['tables'].items()}
        if (manifest['release_id'] != release['release_id']
                or len(manifest['files']) != len(expected)
                or {f['table']: f['rows'] for f in manifest['files']} != expected):
            raise ValueError('immutable manifest conflict')
        for item in manifest['files']:
            if item['path'] != item['table'] + '/part.parquet' or file_sha(root / item['path']) != item['sha256']:
                raise ValueError('immutable Parquet conflict')

    if root.exists():
        verify_existing()
        return root

    schema = pa.schema([('record_json', pa.string())])
    with tempfile.TemporaryDirectory(dir=output, prefix='.semiotic-') as directory:
        staging = Path(directory) / 'release'
        staging.mkdir()
        (staging / 'graph.json').write_bytes(body)
        manifest = {'release_id': release['release_id'], 'files': []}
        for name, rows in release['tables'].items():
            path = staging / name / 'part.parquet'
            path.parent.mkdir()
            with pq.ParquetWriter(path, schema, compression='zstd') as writer:
                for offset in range(0, len(rows), ROW_GROUP_ROWS):
                    records = [encoded(row).decode() for row in rows[offset:offset + ROW_GROUP_ROWS]]
                    writer.write_table(pa.Table.from_arrays([pa.array(records, type=pa.string())], schema=schema))
            manifest['files'].append({'table': name, 'path': str(path.relative_to(staging)),
                'sha256': file_sha(path), 'rows': len(rows)})
        (staging / 'manifest.json').write_bytes(encoded(manifest))
        try:
            staging.rename(root)
        except OSError:
            if not root.is_dir():
                raise
            verify_existing()
    return root


def file_sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def publish(root, s3, athena, bucket, prefix, workgroup):
    """Publish only to a sandbox database and an explicit sandbox S3 prefix."""
    if not prefix.startswith('sandbox/semiotic/') or '..' in prefix or not re.fullmatch(r'[a-z0-9/-]+', prefix):
        raise ValueError('publication prefix must be sandbox/semiotic/...')
    if not bucket or not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', bucket):
        raise ValueError('a valid sandbox bucket is required')
    root = Path(root)
    manifest = json.loads((root / 'manifest.json').read_bytes())
    release_id = manifest['release_id']
    if not re.fullmatch('release_[a-f0-9]{64}', release_id):
        raise ValueError('invalid release ID')
    # Check every local artifact before the first AWS write.
    tables = {'observations', 'chunks', 'mentions', 'bindings', 'edges', 'entities', 'event_versions',
              'language_candidates', 'language_failures', 'observation_geography', 'subject_frequency', 'token_frequency',
              'observation_profiles', 'numerical_tables', 'publication_inputs', 'evidence_units',
              'measurements', 'claims', 'sector_attributions', 'sector_coverage', 'sector_source_codes',
              'industry_groups', 'similarity_groups', 'raw_extraction', 'hybrid_field_values', 'hybrid_field_coverage',
              'unified_observations', 'uuid_index'}
    for item in manifest['files']:
        if item['table'] not in tables or item['path'] != item['table'] + '/part.parquet':
            raise ValueError('invalid manifest member')
        if file_sha(root / item['path']) != item['sha256']:
            raise ValueError('artifact checksum mismatch')
    def put(key, body, checksum=None):
        # Immutable object creation; a replay verifies the existing bytes.
        from botocore.exceptions import ClientError
        with (body.open('rb') if isinstance(body, Path) else io.BytesIO(body)) as stream:
            try:
                s3.put_object(Bucket=bucket, Key=key, Body=stream, IfNoneMatch='*', ServerSideEncryption='AES256')
            except ClientError as error:
                if error.response['Error']['Code'] not in ('PreconditionFailed', '412'):
                    raise
        response = s3.get_object(Bucket=bucket, Key=key)
        try:
            digest = hashlib.sha256()
            for block in iter(lambda: response['Body'].read(1024 * 1024), b''):
                digest.update(block)
            if digest.hexdigest() != (checksum if checksum is not None else sha(body)):
                raise ValueError('remote immutable object mismatch')
        finally:
            response['Body'].close()
    base = prefix.rstrip('/') + '/' + release_id
    db = 'optima_semiotic_sandbox'
    query(athena, f'CREATE DATABASE IF NOT EXISTS {db}', workgroup)
    checks = []
    expected = {}
    for item in manifest['files']:
        key = base + '/' + item['path']
        put(key, root / item['path'], item['sha256'])
        name = item['table'] + '_' + release_id[-16:]
        location = f's3://{bucket}/{base}/{item["table"]}/'
        query(athena, f"CREATE EXTERNAL TABLE IF NOT EXISTS {db}.{name} (record_json string) STORED AS PARQUET LOCATION '{location}'", workgroup)
        table = db + '.' + name
        checks.append(f"SELECT '{table}', count(*), count_if(\"$path\" <> 's3://{bucket}/{key}') FROM {table}")
        expected[table] = [str(item['rows']), '0']
    qid, rows = query(athena, ' UNION ALL '.join(checks), workgroup)
    if len(rows) != len(expected) or {row[0]: row[1:] for row in rows} != expected:
        raise ValueError('Athena count or file location mismatch')
    receipts = [{'table': table, 'query_id': qid, 'rows': int(values[0])}
                for table, values in expected.items()]
    # Last-step commit marker: consumers discover receipts, not loose tables.
    receipt = {'release_id': release_id, 'status': 'published_sandbox', 'tables': receipts,
               'manifest_sha256': sha(encoded(manifest))}
    put(base + '/manifest.json', encoded(manifest))
    # Query IDs change on replay; retain individual verification receipts.
    put(base + '/verifications/' + sha(encoded(receipt)) + '.json', encoded(receipt))
    put(base + '/COMMITTED.json', encoded({'release_id': release_id, 'manifest_sha256': sha(encoded(manifest))}))
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot')
    p.add_argument('--demo', action='store_true')
    p.add_argument('--registry')
    p.add_argument('--output')
    p.add_argument('--capture-job', action='append')
    p.add_argument('--workgroup', default='optima-collected-data')
    p.add_argument('--publish-release')
    p.add_argument('--bucket')
    p.add_argument('--prefix', default='sandbox/semiotic/pilot')
    args = p.parse_args()
    if args.demo:
        # Explicitly synthetic teaching data; never presented as captured evidence.
        observations = [{'observation_id': 'fixture_obs_1', 'record_id': 'fixture_rec_1',
            'quality_status': 'accepted', 'raw_completeness_status': 'complete',
            'raw_s3_uri': 's3://fixture-only/document', 'raw_sha256': 'a' * 64,
            'ingested_at': '2026-11-16T10:00:00Z', 'available_at': None,
            'payload': {'pages': [{'page': 1, 'text': 'Synthetic company CIK 12345 references trial NCT01234567.'}]}}]
        snapshot = {'environment': 'sandbox', 'observations': observations,
                    'observations_sha256': sha(encoded(observations))}
        registry = {'snapshot_id': 'synthetic-current-registry', 'identifiers': [
            {'namespace': 'CIK', 'value': '0000012345', 'entity_id': 'fixture_company', 'review_status': 'verified'}]}
        print(write_release(build(snapshot, registry), args.output))
    elif args.publish_release:
        import boto3
        session = boto3.Session(region_name='us-east-1')
        print(json.dumps(publish(args.publish_release, session.client('s3'), session.client('athena'),
                                 args.bucket, args.prefix, args.workgroup), indent=2))
    elif args.capture_job:
        import boto3
        snapshot = capture(boto3.client('athena', region_name='us-east-1'), args.capture_job, args.workgroup)
        with Path(args.snapshot).open('xb') as stream:
            stream.write(encoded(snapshot))
        print('Captured', len(snapshot['observations']), 'published observations')
    else:
        release = build(json.loads(Path(args.snapshot).read_text()), json.loads(Path(args.registry).read_text()))
        print(write_release(release, args.output))


if __name__ == '__main__':
    main()
