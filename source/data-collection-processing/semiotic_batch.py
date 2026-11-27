"""Benchmark published metadata reads and reconcile bounded sandbox batches."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import date
import json
from pathlib import Path
import re
import tempfile
from time import monotonic

from semiotic_coverage import describe_observations
from semiotic_evidence import build_evidence, graph_observation, unit
from semiotic_grouping import industry_groups, similarity_groups
from semiotic_raw_text import ArchivedEvidenceReader
from semiotic_sectors import TAXONOMY, build_sector_tables
from semiotic_language import analyze, subject_frequency, token_frequency, validate_regions
from semiotic_sandbox import (
    MAX_CAPTURE_BYTES, MAX_CAPTURE_ROWS, build, capture, encoded, file_sha,
    identity, sha, write_release,
)
from semiotic_sandbox import evidence_pages

DATABASE = 'optima_metadata_engine'
TABLE = 'source_observations'


def read_parquet(glue, s3, jobs, bucket, prefix):
    """Use only the registered public partition and its content-addressed file."""
    import pyarrow.parquet as pq

    jobs = sorted(set(jobs))
    if not 1 <= len(jobs) <= 5 or any(not re.fullmatch('[0-9a-f]{64}', job) for job in jobs):
        raise ValueError('supply one to five published job IDs')
    observations, files = [], []
    downloaded = decoded = 0
    for job in jobs:
        part = glue.get_partition(DatabaseName=DATABASE, TableName=TABLE, PartitionValues=[job])['Partition']
        location = part['StorageDescriptor']['Location']
        base = f's3://{bucket}/{prefix.rstrip("/")}/jobs/{job}/data/'
        match = re.fullmatch(re.escape(base) + r'([0-9a-f]{64})/', location)
        if part['Values'] != [job] or not match:
            raise ValueError(f'unexpected published partition location for {job}')
        key = location.removeprefix(f's3://{bucket}/') + 'part.parquet'
        response = s3.get_object(Bucket=bucket, Key=key)
        body = response['Body']
        stored_size = response['ContentLength']
        try:
            if downloaded + stored_size > MAX_CAPTURE_BYTES:
                raise ValueError('Parquet download exceeds the capture byte budget')
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'part.parquet'
                with path.open('wb') as output:
                    for block in iter(lambda: body.read(1024 * 1024), b''):
                        downloaded += len(block)
                        if downloaded > MAX_CAPTURE_BYTES:
                            raise ValueError('Parquet download exceeds the capture byte budget')
                        output.write(block)
                if path.stat().st_size != stored_size or file_sha(path) != match[1]:
                    raise ValueError(f'published Parquet checksum or size mismatch for {job}')
                with pq.ParquetFile(path) as parquet:
                    count = parquet.metadata.num_rows
                    if count <= 0 or len(observations) + count > MAX_CAPTURE_ROWS:
                        raise ValueError('empty partition or capture row budget exceeded')
                    values = []
                    for batch in parquet.iter_batches(batch_size=64, columns=['labelled_json']):
                        for value in batch.column(0).to_pylist():
                            if not isinstance(value, str):
                                raise ValueError('expected labelled_json string')
                            decoded += len(value.encode())
                            if decoded > MAX_CAPTURE_BYTES:
                                raise ValueError('decoded Parquet exceeds the capture byte budget')
                            values.append(value)
                    if len(values) != count:
                        raise ValueError(f'Parquet row count mismatch for {job}')
                    observations.extend(json.loads(value) for value in sorted(values))
            files.append({'job_id': job, 'key': key, 'sha256': match[1], 'bytes': stored_size})
        finally:
            body.close()
    return {'environment': 'sandbox', 'jobs': jobs, 'observations': observations,
            'observations_sha256': sha(encoded(observations))}, files


def benchmark(athena, glue, s3, jobs, bucket, prefix, workgroup):
    started = monotonic()
    direct, files = read_parquet(glue, s3, jobs, bucket, prefix)
    direct_seconds = monotonic() - started
    started = monotonic()
    queried = capture(athena, jobs, workgroup)
    query_seconds = monotonic() - started
    if direct['observations_sha256'] != queried['observations_sha256']:
        raise ValueError('Athena and S3 returned different observation content')
    stats = athena.get_query_execution(QueryExecutionId=queried['query_id'])['QueryExecution'].get('Statistics', {})
    return {'jobs': direct['jobs'], 'rows': len(direct['observations']),
            'observations_sha256': direct['observations_sha256'],
            's3': {'wall_seconds': direct_seconds, 'downloaded_bytes': sum(f['bytes'] for f in files),
                   'files': files},
            'athena': {'wall_seconds': query_seconds, 'bytes_scanned': stats.get('DataScannedInBytes'),
                       'query_id': queried['query_id']}}


def extract(snapshot, registry, byte_limit, language_options=None):
    started = monotonic()
    size = len(encoded(snapshot['observations']))
    if not snapshot['observations'] or len(snapshot['observations']) > MAX_CAPTURE_ROWS or size > byte_limit:
        raise ValueError('empty extraction batch or batch budget exceeded')
    graph = build(snapshot, registry)
    observations = {row['observation_id']: row for row in snapshot['observations']}
    graph['tables']['raw_extraction'] = [
        dict(row['raw_extraction'], id=identity('raw_extraction', [obs_id, row['raw_extraction']]), observation_id=obs_id)
        for obs_id, row in observations.items() if 'raw_extraction' in row]
    graph['tables']['observations'] = [
        graph_observation(observations[row['id']], row) for row in graph['tables']['observations']]
    jobs = snapshot.get('jobs', [])
    graph['tables']['publication_inputs'] = [
        {'id': identity('published_observation', [obs_id, jobs[0]]),
         'observation_id': obs_id, 'job_id': jobs[0]} for obs_id in observations
    ] if len(jobs) == 1 else []
    evidence_units, measurements = build_evidence(observations, graph['tables']['chunks'])
    graph['tables']['evidence_units'] = evidence_units
    graph['tables']['measurements'] = measurements
    claims = graph['tables']['claims'] = []
    language, geography, language_failures = analyze(graph, observations.values(), language_options or {})
    graph['tables']['language_candidates'] = language
    graph['tables']['language_failures'] = language_failures
    graph['tables']['observation_geography'] = geography
    profiles, numerical = describe_observations(
        observations.values(), geography, language, (language_options or {}).get('source_regions', {}))
    graph['tables']['observation_profiles'] = profiles
    graph['tables']['numerical_tables'] = numerical
    chunk_evidence = {row['locator']['chunk_id']: row['id'] for row in evidence_units
                      if row['kind'] == 'extracted_passage'}
    for result in language:
        for triple in result['triples']:
            claim = {'observation_id': result['observation_id'], 'status': 'model_candidate',
                     'evidence_id': chunk_evidence[result['chunk_id']], 'extractor': result['model'],
                     'extractor_version': result['prompt_version'], 'language_candidate_id': result['id'],
                     'eligible_at': None, **triple}
            claims.append(dict(claim, id=identity('claim', claim)))
    cik_mentions = {mention['id'] for mention in graph['tables']['mentions'] if mention['namespace'] == 'CIK'}
    issuer_links = {(edge['subject_id'], edge['object_id']) for edge in graph['tables']['edges']
                    if edge['evidence_id'] in cik_mentions}
    candidates = []
    for item in snapshot.get('reviewed_appointments', []):
        observation = observations[item['observation_id']]
        organization = item['organization_id']
        person = ' '.join(item['reported_appointee'].split())
        if (observation['observation_id'], organization) not in issuer_links or not person:
            raise ValueError('appointment needs a resolved organization and reported appointee')
        if item['role'] not in ('permanent', 'interim'):
            raise ValueError('appointment role must be permanent or interim')
        effective = date.fromisoformat(item['effective_on']).isoformat()
        page = next(p for p in evidence_pages(observation) if p['page'] == item['page'])
        start, end = item['start'], item['end']
        if not 0 <= start < end <= len(page['text']) or page['text'][start:end] != item['quote']:
            raise ValueError('appointment evidence span mismatch')
        event = {'type': 'personnel.appointment', 'organization_id': organization,
                 'reported_appointee_key': person.casefold(), 'role': item['role'], 'effective_on': effective}
        artifact = next((a for a in observation.get('raw_artifacts', [])
                         if page.get('artifact_sha256') and a.get('sha256') == page['artifact_sha256']), None)
        locator = {'coordinate_system': 'unicode_codepoints_in_extracted_page',
                   'page': item['page'], 'start': start, 'end': end}
        excerpt = unit(observation, 'reviewed_passage', locator, artifact=artifact,
                       value=item['quote'], provenance_group_id=item.get('provenance_root'))
        evidence_units.append(excerpt)
        claim = {'observation_id': observation['observation_id'], 'status': 'reviewed_candidate',
                 'evidence_id': excerpt['id'], 'predicate': event['type'],
                 'effective_on': effective, 'eligible_at': None,
                 'participants': [{'role': 'appointing_organization', 'entity_id': organization},
                                  {'role': 'appointee', 'entity_id': None, 'reported_name': person,
                                   'position_kind': item['role']}]}
        claims.append(dict(claim, id=identity('claim', claim)))
        evidence = {'observation_id': observation['observation_id'], 'reported_appointee': person,
                    'page': item['page'], 'start': start, 'end': end, 'quote': item['quote'],
                    'evidence_id': excerpt['id'],
                    'provenance_root': item.get('provenance_root') or observation['observation_id'],
                    'raw_s3_uri': observation['raw_s3_uri'], 'raw_sha256': observation['raw_sha256'],
                    'available_at': observation.get('available_at')}
        candidates.append((event, evidence))
    attributions, coverage, source_codes = build_sector_tables(
        observations, graph['tables'], snapshot.get('reviewed_sector_attributions', ()))
    graph['tables']['sector_attributions'] = attributions
    graph['tables']['sector_coverage'] = coverage
    graph['tables']['sector_source_codes'] = source_codes
    return graph, candidates, {'input_bytes': size, 'rows': len(observations),
                               'extraction_seconds': monotonic() - started}


def reconcile(previous, candidates):
    """One writer merges exact reviewed appointment keys and preserves evidence roots."""
    events = {}
    for row in previous:
        event = {k: v for k, v in row.items() if k not in ('id', 'event_id', 'evidence', 'historically_eligible')}
        events[row['event_id']] = (event, {identity('evidence', item): item for item in row['evidence']})
    for event, item in candidates:
        event_id = identity('event', event)
        _, evidence = events.setdefault(event_id, (event, {}))
        evidence[identity('evidence', item)] = item
    result = []
    for event_id, (event, evidence) in sorted(events.items()):
        row = dict(event, event_id=event_id, evidence=[evidence[key] for key in sorted(evidence)],
                   historically_eligible=False)
        result.append(dict(row, id=identity('event_version', row)))
    return result


def run_batches(snapshots, registry, previous=None, *, workers=2, byte_limit=MAX_CAPTURE_BYTES,
                language_options=None, similarity_input=None):
    if not 1 <= workers <= 4 or not 0 < byte_limit <= MAX_CAPTURE_BYTES:
        raise ValueError('invalid extraction worker or byte limit')
    language_options = language_options or {}
    validate_regions(language_options.get('source_regions', {}))
    if language_options.get('model') and not 1 <= language_options.get('port', 0) <= 65535:
        raise ValueError('invalid loopback language server port')
    if previous is not None:
        prior_content = {k: v for k, v in previous.items() if k != 'release_id'}
        if previous.get('environment') != 'sandbox' or identity('release', prior_content) != previous['release_id']:
            raise ValueError('previous graph release checksum mismatch')
    tables, candidates, inputs, metrics = {}, [], [], []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        # Submit at most one wave at a time rather than queuing the whole run.
        from itertools import islice
        source = iter(snapshots)
        while batch := list(islice(source, workers)):
            futures = [pool.submit(extract, snapshot, registry, byte_limit, language_options) for snapshot in batch]
            for future in futures:
                graph, proposed, measurement = future.result()
                inputs.append(graph['input_sha256'])
                metrics.append(measurement)
                candidates.extend(proposed)
                for name, rows in graph['tables'].items():
                    target = tables.setdefault(name, {})
                    for row in rows:
                        if target.setdefault(row['id'], row) != row:
                            raise ValueError(f'conflicting {name} identity {row["id"]}')
    if not inputs:
        raise ValueError('at least one input batch is required')
    registry_sha = sha(encoded(registry))
    if previous and previous['registry_sha256'] != registry_sha:
        raise ValueError('registry changed; reconcile identity changes explicitly before extending ledger')
    ledger = reconcile(previous['tables']['event_versions'] if previous else [], candidates)
    release = {'environment': 'sandbox', 'version': 'semiotic-batch-4',
               'sector_taxonomy_version': TAXONOMY['taxonomy_version'],
               'sector_taxonomy_sha256': sha(encoded(TAXONOMY)),
               'registry_sha256': registry_sha, 'batch_inputs': sorted(inputs),
               'parent_release_id': previous['release_id'] if previous else None,
               'tables': {name: [rows[key] for key in sorted(rows)] for name, rows in tables.items()}}
    release['tables']['event_versions'] = ledger
    release['tables']['subject_frequency'] = subject_frequency(tables['language_candidates'].values())
    release['tables']['token_frequency'] = token_frequency(tables['language_candidates'].values())
    release['tables']['industry_groups'] = industry_groups(release['tables']['sector_attributions'])
    release['tables']['similarity_groups'] = (
        similarity_groups(release['tables'], similarity_input) if similarity_input is not None else [])
    release['release_id'] = identity('release', release)
    return release, metrics


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    bench = sub.add_parser('benchmark')
    bench.add_argument('--job', action='append', required=True)
    bench.add_argument('--config', default=str(Path(__file__).parent / 'config/metadata-engine.json'))
    run = sub.add_parser('run')
    inputs = run.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--snapshot', action='append', type=Path, help='one frozen snapshot per extraction batch')
    inputs.add_argument('--job', action='append', help='one published metadata job per extraction batch')
    run.add_argument('--reader', choices=('s3', 'athena'), default='s3')
    run.add_argument('--metadata-only', action='store_true', help='skip archive reads for live jobs')
    run.add_argument('--config', default=str(Path(__file__).parent / 'config/metadata-engine.json'))
    run.add_argument('--registry', type=Path, required=True)
    run.add_argument('--previous-release', type=Path)
    run.add_argument('--output', type=Path, required=True)
    run.add_argument('--workers', type=int, default=2)
    run.add_argument('--batch-bytes', type=int, default=MAX_CAPTURE_BYTES)
    run.add_argument('--similarity-input', type=Path, help='optional versioned embedding fixture and as-of cutoff')
    run.add_argument('--llm-model', help='model alias served by on-host llama.cpp; enables language analysis')
    run.add_argument('--llm-port', type=int, default=8080, help='llama.cpp loopback port')
    run.add_argument('--source-regions', type=Path,
                     default=Path(__file__).parent / 'config/semiotic-source-regions.json',
                     help='source_key to region and evidence reference JSON mapping')
    args = p.parse_args()
    if args.action == 'benchmark' or args.job:
        import boto3
        config = json.loads(Path(args.config).read_text())
        session = boto3.Session(region_name=config['region'])
    if args.action == 'benchmark':
        receipt = benchmark(session.client('athena'), session.client('glue'), session.client('s3'),
                            args.job, config['bucket'], config['prefix'], config['athena_workgroup'])
    else:
        previous = json.loads(args.previous_release.read_text()) if args.previous_release else None
        if args.snapshot:
            snapshots = (json.loads(path.read_text()) for path in args.snapshot)
        elif args.reader == 's3':
            glue, s3 = session.client('glue'), session.client('s3')
            snapshots = (read_parquet(glue, s3, [job], config['bucket'], config['prefix'])[0]
                         for job in dict.fromkeys(args.job))
        else:
            athena = session.client('athena')
            snapshots = (capture(athena, [job], config['athena_workgroup']) for job in dict.fromkeys(args.job))
        if args.job and not args.metadata_only:
            archived = ArchivedEvidenceReader(session.client('s3'), config['bucket'])
            snapshots = map(archived.hydrate, snapshots)
        release, metrics = run_batches(snapshots, json.loads(args.registry.read_text()), previous,
                                       workers=args.workers, byte_limit=args.batch_bytes,
                                       similarity_input=json.loads(args.similarity_input.read_text())
                                       if args.similarity_input else None,
                                       language_options={'model': args.llm_model, 'port': args.llm_port,
                                           'source_regions': json.loads(args.source_regions.read_text())})
        receipt = {'release': str(write_release(release, args.output)), 'batches': metrics}
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
