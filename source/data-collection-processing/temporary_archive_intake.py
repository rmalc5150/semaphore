"""Process staged source archives into S3 data products and metadata-engine jobs."""
import argparse
import base64
from collections import Counter, defaultdict
import csv
from datetime import date, timedelta
import fcntl
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
import pyarrow as pa
import pyarrow.parquet as pq

from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, task_spec
from metadata_engine.temporary_archives import DATASET, VERSION, check_object, contracts, processing_prefix
from research_contract import canonical_json, digest, load_json, seal_record
from temporary_archive_formats import archive_rows
from temporary_archive_stage import ACCOUNT, BUCKET, CONTROL, FERC_PARQUET, REGION, source_id, staged_key

ROOT = Path(__file__).resolve().parent
PROVIDERS = {
    123: 'https://api.globalenergymonitor.org/assets',
    189: 'https://ec.europa.eu/safety-gate-alerts/screen/webReport',
    235: 'https://gis.cdc.gov/flu2/PostPhase02DataDownload',
    254: 'https://data.fca.org.uk/#/nsm/nationalstoragemechanism',
    255: 'https://www.cnmv.es/portal/Consultas/Directivos-Consulta',
    256: 'https://www.nbim.no/en/investments/all-investments/',
    266: 'https://www.ferc.gov/power-sales-and-markets/regulatory-disclosures/electric-quarterly-reports-eqr',
}
SUPPORTING = {
    'FERC/datapackage.json', 'FERC-Verified-Local-Files.csv', 'FERC-Transactions-Download-Index.csv',
    'FERC-Q1-2016-Filing-Dates.csv', 'FERC-Contracts-2016Q1-to-2026Q3.zip',
}
ROW_SCHEMA = pa.schema([
    ('source_member', pa.string()), ('native_row', pa.int64()), ('native_id', pa.string()),
    ('period', pa.string()), ('period_basis', pa.string()), ('native_json', pa.string()),
])
MISSING = ('NoSuchKey', '404', 'NotFound')


def exact_bytes(s3, key, sha=None):
    with s3.get_object(Bucket=BUCKET, Key=key, ExpectedBucketOwner=ACCOUNT)['Body'] as stream:
        body = stream.read()
    if sha and hashlib.sha256(body).hexdigest() != sha:
        raise ValueError('checksum_mismatch_for_' + key.rsplit('/', 1)[-1])
    return body


def sha_for(item):
    return base64.b64decode(item['sha256_base64'], validate=True).hex()


def put_checked(s3, key, body, sha, size, media):
    try:
        s3.put_object(Bucket=BUCKET, Key=key, Body=body, ContentType=media, ServerSideEncryption='AES256',
                      ChecksumSHA256=base64.b64encode(bytes.fromhex(sha)).decode(), IfNoneMatch='*',
                      ExpectedBucketOwner=ACCOUNT)
    except ClientError as error:
        if error.response['Error']['Code'] not in ('412', 'PreconditionFailed'):
            raise
    check_object(s3, BUCKET, key, sha, size)
    return {'s3_uri': f's3://{BUCKET}/{key}', 'sha256': sha, 'bytes': size}


def put_json(s3, key, document):
    body = canonical_json(document) + b'\n'
    return put_checked(s3, key, body, hashlib.sha256(body).hexdigest(), len(body), 'application/json')


class S3RandomAccess(io.RawIOBase):
    """Read Parquet footers with bounded range requests."""
    def __init__(self, s3, item):
        self.s3, self.item, self.position = s3, item, 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, position, whence=io.SEEK_SET):
        self.position = (0, self.position, self.item['bytes'])[whence] + position
        if self.position < 0:
            raise ValueError('negative_read_position')
        return self.position

    def readinto(self, target):
        size = min(len(target), self.item['bytes'] - self.position)
        if size <= 0:
            return 0
        if size > 32 * 1024**2:
            raise ValueError('archive_range_read_too_large')
        end = self.position + size - 1
        response = self.s3.get_object(Bucket=BUCKET, Key=self.item['key'],
                                      Range=f'bytes={self.position}-{end}', IfMatch=self.item['etag'])
        with response['Body'] as stream:
            body = stream.read()
        if len(body) != size:
            raise ValueError('incorrect_archive_range_length')
        target[:size] = body
        self.position += size
        return size


def ferc_index(s3, items):
    package = items.get('FERC/datapackage.json')
    counts = items.get('FERC-Verified-Local-Files.csv')
    if not package or not counts:
        raise ValueError('ferc_publisher_package_and_inventory_required')
    release = json.loads(exact_bytes(s3, package['key'], sha_for(package)))
    checks = {
        row['file']: (int(row['rows']), int(row['bytes']))
        for row in csv.DictReader(io.StringIO(exact_bytes(s3, counts['key'], sha_for(counts)).decode('utf-8-sig')))
    }
    resources = {}
    for resource in release['resources']:
        if resource['name'] in ('core_ferceqr__contracts', 'core_ferceqr__transactions'):
            columns = [field['name'] for field in resource['schema']['fields']]
            for part in resource['parts']:
                resources[part['path']] = (columns, part['bytes'], part['hash'])
    return resources, checks, release['version']


def parse_ferc(s3, item, raw, ferc):
    quarter, category = FERC_PARQUET.fullmatch(item['inbox_key']).groups()
    resources, checks, release = ferc
    path = f'core_ferceqr__{category}/{quarter}.parquet'
    columns, size, sha = resources[path]
    if raw['source_url'] != f'https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/ferceqr/{path}':
        raise ValueError('ferc_parquet_source_mismatch')
    if size != raw['bytes'] or sha != 'sha256:' + raw['sha256']:
        raise ValueError('ferc_parquet_does_not_match_publisher_sha256')
    with S3RandomAccess(s3, item) as source:
        parquet = pq.ParquetFile(source)
        count = parquet.metadata.num_rows
        schema = [[field.name, str(field.type)] for field in parquet.schema_arrow]
        if (columns != [name for name, _ in schema]
                or (count, size) != checks[Path(item['inbox_key']).name] or count <= 0):
            raise ValueError('ferc_parquet_schema_or_count_mismatch')
        groups = parquet.metadata.num_row_groups
    return {
        'representation': 'PUDL FERC EQR publisher Parquet release',
        'publisher_release': release, 'rows': count, 'period_min': quarter, 'period_max': quarter,
        'period_basis': 'reporting_quarter', 'tables': {category: count},
    }, [{
        'dataset': category, 'rows': count, 'row_groups': groups, 'schema': schema,
        'object': {k: raw[k] for k in ('s3_uri', 'sha256', 'bytes')},
    }]


def download_archive(s3, item, raw, original):
    with original.open('wb') as output:
        response = s3.get_object(Bucket=BUCKET, Key=item['key'], IfMatch=item['etag'])
        checksum = hashlib.sha256()
        with response['Body'] as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                output.write(block)
                checksum.update(block)
    if original.stat().st_size != raw['bytes'] or checksum.hexdigest() != raw['sha256']:
        raise ValueError('archive_download_does_not_match_stage')


def create_parquets(s3, item, raw, prefix, workspace):
    original = workspace / 'archive.zip'
    download_archive(s3,item,raw,original)
    if item['inbox_key']=='FERC-Official-Q1-2016-Filings.zip':
        from ferc_official_handoff import prepare
        return prepare(s3,original,raw,prefix,workspace)
    writers = {}
    pending = defaultdict(list)
    counts = Counter()
    members = defaultdict(Counter)
    bounds = {}

    def flush(table):
        batch = pending[table]
        if batch:
            writers[table].write_table(pa.Table.from_pylist(batch, schema=ROW_SCHEMA))
            batch.clear()

    try:
        for table, member, native_id, period, basis, row in archive_rows(original, item['source'], item['inbox_key']):
            if table not in writers:
                writers[table] = pq.ParquetWriter(workspace/f'{table}.parquet', ROW_SCHEMA, compression='zstd')
            members[table][member] += 1
            counts[table] += 1
            if period:
                key = (table, basis)
                start, end = bounds.get(key, (period, period))
                bounds[key] = (min(start, period), max(end, period))
            pending[table].append({
                'source_member': member, 'native_row': members[table][member], 'native_id': native_id,
                'period': period, 'period_basis': basis,
                'native_json': canonical_json(row).decode('utf-8'),
            })
            if len(pending[table]) == 4096:
                flush(table)
        for table in writers:
            flush(table)
    finally:
        for writer in writers.values():
            writer.close()
    if not counts:
        raise ValueError('empty_archive_dataset')

    tables = []
    for table, count in sorted(counts.items()):
        path = workspace/f'{table}.parquet'
        with path.open('rb') as file:
            sha = hashlib.file_digest(file, 'sha256').hexdigest()
            file.seek(0)
            ref = put_checked(s3, f'{prefix}/tables/{table}/{sha}/data.parquet', file, sha, path.stat().st_size,
                              'application/vnd.apache.parquet')
        tables.append({
            'dataset': table, 'rows': count, 'object': ref, 'members': dict(members[table]),
            'periods': {basis: list(interval) for (name, basis), interval in sorted(bounds.items()) if name == table},
            'schema': [[field.name, str(field.type)] for field in ROW_SCHEMA],
        })
    representation = {
        'CNMV-Legacy-2016.zip': 'CNMV legacy filing listings with checksum-matched original PDFs',
        'CNMV-Modern-Register-Snapshot.zip': 'CNMV current registration snapshot with retained search-page evidence',
        'GEM-Current-Entities.zip': 'Current GEM entity API snapshot',
        'FCA-PDMR-Notice-Index.zip': 'FCA notice-index records verified against original dated CSV exports',
        'NBIM-Opening-2015.zip': 'NBIM 2015 opening API holdings reconciled to corresponding CSV exports',
    }.get(item['inbox_key']) or {
        123: 'Current GEM asset API snapshot, including reported owner fields where provided',
        255: 'CNMV notification results checked against archived search pages; individual filing documents are linked only',
    }.get(item['source'], 'Supplied archive of native provider exports')
    return {'representation': representation, 'rows': sum(counts.values()), 'tables': dict(counts)}, tables


def process(s3, item, ferc, scratch):
    raw_sha = sha_for(item)
    key, size = item['key'], item['bytes']
    check_object(s3, BUCKET, key, raw_sha, size)
    number = item['source']
    source = f'market_source_{number}'
    prefix = processing_prefix(source, key)
    manifest_key = f'{prefix}/manifest.json'
    url = PROVIDERS[number]
    if item['inbox_key']=='GEM-Current-Entities.zip':
        url = 'https://api.globalenergymonitor.org/entities'
    if match := FERC_PARQUET.fullmatch(item['inbox_key']):
        quarter, category = match.groups()
        url = f'https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/ferceqr/core_ferceqr__{category}/{quarter}.parquet'
    raw = {'s3_uri': f's3://{BUCKET}/{key}', 'sha256': raw_sha, 'bytes': size,
           'source_url': url, 'retrieved_at': item['staged_at'], 'inbox_key': item['inbox_key']}
    if 'attachment' in item:
        raw['attachment'] = item['attachment']
    try:
        existing = exact_bytes(s3, manifest_key)
    except ClientError as error:
        if error.response['Error']['Code'] not in MISSING:
            raise
    else:
        result = json.loads(existing)
        if result['raw'] != raw or result['version'] != VERSION or result['source'] != source:
            raise ValueError('processing_manifest_conflicts_with_staged_object')
        return result, {'s3_uri': f's3://{BUCKET}/{manifest_key}', 'sha256': hashlib.sha256(existing).hexdigest()}
    if match:
        summary, tables = parse_ferc(s3, item, raw, ferc)
    else:
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            summary, tables = create_parquets(s3, item, raw, prefix, Path(directory))
    result = {'version': VERSION, 'source': source, 'raw': raw, 'summary': summary, 'tables': tables}
    return result, put_json(s3, manifest_key, result)


def load_universe(s3):
    infra = load_json(ROOT/'config/constellation-infrastructure.json')
    state = json.loads(exact_bytes(s3, infra['legacy_seed_key']))
    entry = state['paths']['config/company-universe.v0.5.json']
    return json.loads(exact_bytes(s3, entry['key'], entry['sha256']))


def collected_record(run, manifest, processing):
    raw = manifest['raw']
    return seal_record({
        'document_type': 'collected_record', 'schema_version': '1.0',
        'source': manifest['source'], 'dataset': DATASET,
        'source_record_id': digest([raw['inbox_key'], raw['sha256']]), 'source_record_id_basis': 'documented_composite',
        'source_url': raw['source_url'], 'event_at': None, 'available_at': None, 'source_updated_at': None,
        'availability_basis': 'unknown', 'availability_evidence': [], 'ingested_at': raw['retrieved_at'],
        'run_id': run.run_id, 'universe_version': run.universe['universe_version'], 'company_ids': [], 'listing_ids': [],
        'person_ids': [], 'product_ids': [], 'entity_match_status': 'unresolved',
        'payload': {
            'source_evidence': [raw], 'data': {'processing_manifest_s3_uri': processing['s3_uri'],
                'processing_manifest_sha256': processing['sha256'], 'summary': manifest['summary']},
            'point_in_time_eligible': False,
        },
    })


def commit(store, settings, universe, taxonomy, manifest, processing):
    raw = manifest['raw']
    staged_day = date.fromisoformat(raw['retrieved_at'][:10])
    spec = task_spec(manifest['source'], DATASET, 'historical', f'{staged_day}T00:00:00Z',
                     f'{staged_day + timedelta(days=1)}T00:00:00Z',
                     {'inbox_key': raw['inbox_key'], 'archive_sha256': raw['sha256']},
                     VERSION, universe, taxonomy)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=True)
    except AlreadyComplete as done:
        key = str(done)
    else:
        if not run.exhausted:
            run.commit_page([collected_record(run, manifest, processing)], exhausted=True)
        key = run.finish('complete', expected_records=1)
    final = json.loads(store.get(key).body)
    head = json.loads(store.get('checkpoints/'+final['task_id']+'/head.json').body)
    if final['status'] != 'complete' or final['record_count'] != 1 or key not in head['terminal_history']:
        raise ValueError('archive_collection_manifest_not_committed')
    batch = final['pages'][0]['batches'][0]['key']
    return key, 'research-data/' + batch


def process_metadata(db, s3, source, key):
    """Lease this intake's exact job on the upload host before exposing it to the shared queue."""
    from metadata_engine.controller import register_contract
    from metadata_engine.runtime_db import fingerprint
    from metadata_engine.worker import process as process_job

    etag = s3.head_object(Bucket=BUCKET, Key=key)['ETag']
    job_id = fingerprint([source, key, etag, 'legacy_batch', VERSION])
    with db.tx() as cursor:
        register_contract(db, contracts()[source], cursor)
        cursor.execute('SELECT state,contract_version FROM engine_sources WHERE source_key=%s FOR UPDATE', (source,))
        state = cursor.fetchone()
        if state != {'state': 'enabled', 'contract_version': VERSION}:
            raise RuntimeError('archive_metadata_source_not_enabled')
        db.enqueue(source, key, etag, 'legacy_batch', 40, cursor)
        cursor.execute('SELECT *,lease_until>=UTC_TIMESTAMP(6) AS active_lease FROM engine_jobs WHERE job_id=%s FOR UPDATE',
                       (job_id,))
        job = cursor.fetchone()
        if job['state'] == 'accepted':
            return job_id
        if job['state'] == 'running' and job['active_lease']:
            raise RuntimeError('archive_metadata_job_already_leased')
        token = str(uuid4())
        cursor.execute("""UPDATE engine_jobs SET state='running',lease_token=%s,
                       lease_until=DATE_ADD(UTC_TIMESTAMP(6), INTERVAL 30 MINUTE),attempts=attempts+1
                       WHERE job_id=%s""", (token, job_id))
        job['lease_token'] = token
    process_job(db, s3, db.config, job)
    with db.tx() as cursor:
        cursor.execute('SELECT state,reason,output_rows FROM engine_jobs WHERE job_id=%s', (job_id,))
        outcome = cursor.fetchone()
        if outcome['state'] == 'retry':
            cursor.execute("""UPDATE engine_jobs SET available_after=DATE_ADD(UTC_TIMESTAMP(6), INTERVAL 1 DAY)
                           WHERE job_id=%s AND state='retry' AND lease_token=%s""", (job_id, token))
    if outcome['state'] != 'accepted' or outcome['output_rows'] != 1:
        raise RuntimeError(f"archive_metadata_{outcome['state']}:{outcome['reason']}")
    return job_id


def run(args):
    from metadata_engine.runtime_db import Database

    s3 = boto3.client('s3', region_name=REGION)
    if not re.fullmatch(r'[0-9a-f]{64}', args.sha256):
        raise ValueError('invalid_inventory_sha256')
    if args.inventory != f'{CONTROL}/inventories/{args.sha256}.json':
        raise ValueError('unexpected_inventory_key')
    inventory = json.loads(exact_bytes(s3, args.inventory, args.sha256))
    if inventory['version'] != 1:
        raise ValueError('unexpected_staging_inventory_version')
    items = {item['inbox_key']: item for item in inventory['objects']}
    if len(items) != len(inventory['objects']) or any(
        item['source'] != source_id(key) or item['key'] != staged_key(key, item['inbox_etag'], item['bytes'])
        for key, item in items.items()
    ):
        raise ValueError('unexpected_or_duplicate_staged_input')
    if args.key and (set(args.key) - items.keys() or set(args.key) & SUPPORTING):
        raise ValueError('selected_data_key_is_missing_or_supporting_only')
    selected = [item for key, item in items.items() if key not in SUPPORTING and (not args.key or key in args.key)]
    ferc = ferc_index(s3, items) if any(FERC_PARQUET.fullmatch(item['inbox_key']) for item in selected) else None
    # Process the small provider exports ahead of the 86 FERC quarterly files.
    selected.sort(key=lambda item: (bool(FERC_PARQUET.fullmatch(item['inbox_key'])), item['inbox_key']))
    settings = StorageSettings.load(ROOT/'config/collection-storage.s3.json')
    store = settings.store(s3)
    universe = load_universe(s3)
    taxonomy = load_json(ROOT/'config/sectors.v1.json')
    db = Database(load_json(ROOT/'config/metadata-engine.json'))
    done, errors = [], []
    for item in selected:
        try:
            manifest, processing = process(s3, item, ferc, args.scratch)
            final, input_key = commit(store, settings, universe, taxonomy, manifest, processing)
            job_id = process_metadata(db, s3, manifest['source'], input_key)
            result = {'object': item['inbox_key'], 'source': manifest['source'], 'summary': manifest['summary'],
                      'processing_manifest': processing['s3_uri'], 'collection_manifest': final,
                      'input_key': input_key, 'metadata_job_id': job_id}
            done.append(result)
            print(json.dumps({'status': 'committed_and_metadata_accepted', **result}), flush=True)
        except (ClientError, OSError, ValueError, RuntimeError) as error:
            result = {'object': item['inbox_key'], 'error': type(error).__name__, 'reason': str(error)[:400]}
            errors.append(result)
            print(json.dumps({'status': 'failed', **result}), flush=True)
    receipt = {'inventory': args.inventory, 'processed': done, 'errors': errors,
               'retained_as_support': sorted(SUPPORTING & items.keys()), 'ignored': inventory['ignored']}
    receipt_sha = digest(receipt)
    ref = put_json(s3, f'{CONTROL}/runs/{receipt_sha}.json', receipt)
    print(json.dumps({'receipt': ref['s3_uri'], 'objects_committed': len(done), 'errors': len(errors),
                      'native_rows': sum(result['summary']['rows'] for result in done)}), flush=True)
    return int(bool(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--scratch', type=Path, default=Path('/opt/constellation/tmp'))
    parser.add_argument('--key', action='append', help='Process only these staged data files')
    args = parser.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    with (args.scratch/'.temporary-archive-intake.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
