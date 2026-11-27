"""Retain original Canadian SEDI issuer event reports and commit their filing rows."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import fcntl
import hashlib
import io
import json
from pathlib import Path
import re
from zipfile import ZipFile

import boto3

from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, task_spec
from market_archive_import import RESULTS, read_universe
from market_source_capture import MARKET, immutable_put, utcnow
from market_source_register import ROOT, write
from metadata_engine.sedi import DATASET, SOURCE, SOURCE_URL, VERSION, parse_pdf
from research_contract import digest, load_json, seal_record

RAW_PREFIX = f'{MARKET}/historical-exports/{SOURCE}'
MAX_BYTES = 64 * 1024**2
SCOPE = 'Public SEDI issuer event history by filing date'
NAME_PATTERN = re.compile(r'SEDI-Issuer-Report-History_(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})\.pdf')
IDENTITY_FIELDS = ('issuer_name', 'filing_date', 'event_type', 'effective_date', 'title', 'details', 'report_occurrence')


def inputs(path, package):
    if path.suffix.lower() == '.pdf':
        return [(path.name, package)]
    if path.suffix.lower() != '.zip':
        raise ValueError('SEDI requires a PDF report or a ZIP of PDF reports')
    with ZipFile(io.BytesIO(package)) as archive:
        members = [member for member in archive.infolist() if not member.is_dir()]
        if (not members or sum(member.file_size for member in members) > MAX_BYTES
                or len({member.filename for member in members}) != len(members)
                or any(not member.filename.lower().endswith('.pdf') for member in members)):
            raise ValueError('expected distinct SEDI PDFs within the ZIP size limit')
        return [(member.filename, archive.read(member)) for member in members]


def prepare(item):
    name, body = item
    report = parse_pdf(body)
    start, end = report['first_day'], report['last_day']
    if (match := NAME_PATTERN.fullmatch(Path(name).name)) and match.groups() != (start, end):
        raise ValueError(f'SEDI report filename and printed filing dates differ in {name}')
    return name, body, report, hashlib.sha256(body).hexdigest()


def retain(s3, bucket, key, body, sha, media):
    immutable_put(s3, bucket, key, body, sha, media, verify=True)
    return f's3://{bucket}/{key}'


def record(run, row, evidence):
    identity = digest([row[field] for field in IDENTITY_FIELDS])
    return seal_record({
        'document_type': 'collected_record', 'schema_version': '1.0', 'source': SOURCE, 'dataset': DATASET,
        'source_record_id': identity, 'source_record_id_basis': 'documented_composite',
        'source_url': SOURCE_URL,
        'event_at': {'value': row['effective_date'], 'precision': 'day', 'source_timezone': 'America/Toronto'},
        'available_at': None, 'source_updated_at': None, 'availability_basis': 'unknown',
        'availability_evidence': [], 'ingested_at': evidence['retrieved_at'], 'run_id': run.run_id,
        'universe_version': run.universe['universe_version'], 'company_ids': [], 'listing_ids': [],
        'person_ids': [], 'product_ids': [], 'entity_match_status': 'unresolved',
        'payload': {'data': row, 'source_evidence': [evidence], 'scope': SCOPE, 'point_in_time_eligible': False},
    })


def commit(store, settings, universe, taxonomy, evidence, rows):
    start, end = evidence['start'], evidence['end']
    day_after = date.fromisoformat(end) + timedelta(days=1)
    spec = task_spec(
        SOURCE, DATASET, 'historical', f'{start}T00:00:00Z', f'{day_after}T00:00:00Z',
        {'source_id': 253, 'filing_date_start': start, 'filing_date_end': end, 'original_sha256': evidence['sha256']},
        VERSION, universe, taxonomy,
    )
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=True)
    except AlreadyComplete as complete:
        final = str(complete)
    else:
        if not run.exhausted:
            run.commit_page((record(run, row, evidence) for row in rows), next_cursor=None, exhausted=True)
        final = run.finish('complete', expected_records=len(rows))
    manifest = json.loads(store.get(final).body)
    if manifest['record_count'] != len(rows):
        raise ValueError('SEDI completed manifest record count differs from PDF')
    return final


def import_archive(path, session):
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('SEDI upload exceeds size limit')
    package = path.read_bytes()
    with ThreadPoolExecutor(max_workers=2) as executor:
        reports = list(executor.map(prepare, inputs(path, package)))

    settings = StorageSettings.load(ROOT/'config/collection-storage.s3.json')
    bucket = settings.s3_bucket
    s3 = session.client('s3')
    store = settings.store(s3)
    current = load_json(RESULTS) if RESULTS.exists() else {}
    covered = [item['raw'] for item in current.values() if item.get('source') == SOURCE and item.get('manifest')]
    for name, _, report, sha in reports:
        start, end = report['first_day'], report['last_day']
        if any(r['start'] <= end and start <= r['end'] and r['sha256'] != sha for r in covered):
            raise ValueError(f'SEDI filing window overlaps a different committed or supplied report in {name}')
        covered.append({'start': start, 'end': end, 'sha256': sha})

    archive_ref = {}
    if path.suffix.lower() == '.zip':
        archive_sha = hashlib.sha256(package).hexdigest()
        archive_uri = retain(s3, bucket, f'{RAW_PREFIX}/archives/{archive_sha}.zip',
                             package, archive_sha, 'application/zip')
        archive_ref = {'archive_s3_uri': archive_uri, 'archive_sha256': archive_sha}
    universe = read_universe(s3, bucket)
    taxonomy = load_json(ROOT/'config/sectors.v1.json')
    results = []
    for name, body, report, sha in reports:
        start, end = report['first_day'], report['last_day']
        key = f'sedi-issuer-events-{start}_{end}-{sha}'
        if key in current:
            results.append(current[key])
            continue
        uri = retain(s3, bucket, f'{RAW_PREFIX}/{DATASET}/{start}_{end}/{sha}.pdf', body, sha, 'application/pdf')
        evidence = {
            's3_uri': uri, 'sha256': sha, 'source_url': SOURCE_URL, 'retrieved_at': utcnow().isoformat(),
            'member': name, 'start': start, 'end': end, 'bytes': len(body), 'method': 'manual_original',
            'report_generated_at_et': report['report_generated_at_et'], **archive_ref,
        }
        rows = report['rows']
        manifest = commit(store, settings, universe, taxonomy, evidence, rows)
        result = {
            'id': 253, 'source': SOURCE, 'dataset': DATASET, 'scope': SCOPE, 'records': len(rows),
            'raw': evidence, 'manifest': manifest, 'first_filing_date': min(row['filing_date'] for row in rows),
            'last_filing_date': max(row['filing_date'] for row in rows),
        }
        current[key] = result
        write(RESULTS, current)
        results.append(result)
        print(f'{start} through {end}: {len(rows)} issuer events', flush=True)
    return list({result['manifest']: result for result in results}.values())


def queue_metadata(session, results):
    from market_archive_athena import BUCKET, PREFIX, native_batches
    from metadata_engine.controller import enqueue_objects, register_contract
    from metadata_engine.runtime_db import Database

    config = load_json(ROOT/'config/metadata-engine.json')
    s3 = session.client('s3')
    entries = native_batches(s3, results)[SOURCE, DATASET]
    objects = [
        {'Key': PREFIX+key, 'ETag': s3.head_object(Bucket=BUCKET, Key=PREFIX+key)['ETag']}
        for key in entries
    ]
    db = Database(config, session)
    with db.tx() as cursor:
        register_contract(db, config['contracts'][SOURCE], cursor)
        return enqueue_objects(db, objects, 'legacy_batch', 40, cursor)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--publish-and-queue', action='store_true', help='Verify in Athena and queue metadata processing')
    args = parser.parse_args()
    session = boto3.Session(region_name='us-east-1')
    with (ROOT/'.sedi-archive-import.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        results = import_archive(args.archive, session)
        queued = None
        if args.publish_and_queue:
            from market_archive_athena import main as publish_archive

            publish_archive(['--source', '253'])
            queued = queue_metadata(session, results)
    print(json.dumps({'reports': len(results), 'records': sum(result['records'] for result in results),
                      'metadata_inputs_enqueued': queued}))


if __name__ == '__main__':
    main()
