#!/usr/bin/env python3
"""Verified source observations and coverage for DOI-registered proceedings."""
import fcntl
import hashlib
import json
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from collection_storage import StorageSettings
from regulatory_athena import read_inputs
from research_contract import ROOT, canonical_json, digest, load_json
from window_publication import publish_pending
import sec_athena_pilot as release

SCHEMAS = {
    'conference_observations': [(n, 'string') for n in ('record_id', 'observation_id', 'doi', 'title',
        'publication_date', 'ingested_at', 'source_url', 'data_json', 'record_json')] +
        [('source_manifests', 'array<string>'), ('source_document_keys', 'array<string>'), ('point_in_time_eligible', 'boolean')],
    'conference_coverage': [(n, 'string') for n in ('source_manifest', 'mode', 'window_start', 'window_end_exclusive',
        'date_filter', 'coverage_note')] + [('records', 'bigint')]
}


def prepare(store, settings, config, keys, output_root):
    release.validate_config(config)
    import tempfile
    import shutil
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.stream-', dir=output_root))
    observation_path = stage / 'observations.parquet'
    schema = pa.schema([(n, release.ARROW_TYPES[t]) for n, t in SCHEMAS['conference_observations']])
    writer = pq.ParquetWriter(observation_path, schema, compression='snappy', version='1.0', use_dictionary=False)
    buffer = []
    buffer_bytes = 0
    observation_count = 0
    expected_hash = hashlib.sha256()

    def flush():
        nonlocal buffer_bytes
        if buffer:
            writer.write_table(pa.Table.from_pylist(buffer, schema=schema), row_group_size=64)
            buffer.clear()
            buffer_bytes = 0

    def consume(entry):
        nonlocal buffer_bytes, observation_count
        record = entry['record']; payload = record['payload']
        row = {'record_id': record['record_id'], 'observation_id': record['observation_id'],
            'doi': record['source_record_id'], 'title': payload['title'],
            'publication_date': record['event_at']['value'] if record['event_at'] else None,
            'ingested_at': record['ingested_at'], 'source_url': record['source_url'],
            'data_json': release.json_text(payload['data']), 'record_json': release.json_text(record),
            'source_manifests': sorted(entry['manifests']),
            'source_document_keys': sorted({e['key'] for e in payload['source_evidence']}),
            'point_in_time_eligible': False}
        encoded = canonical_json(row) + b'\n'
        expected_hash.update(encoded)
        buffer.append(row); buffer_bytes += len(encoded); observation_count += 1
        if len(buffer) >= 64 or buffer_bytes >= 2 * 1024 * 1024:
            flush()

    try:
        _, universe, inputs = read_inputs(store, keys, allowed={'crossref_proceedings'}, dataset='conference_records', consume=consume)
        flush()
    except BaseException:
        writer.close()
        shutil.rmtree(stage)
        raise
    else:
        writer.close()
    # Read bounded batches, checking every normalized value rather than retaining
    # a second full Arrow table for the round-trip check.
    actual_hash = hashlib.sha256(); actual_count = 0
    for batch in pq.ParquetFile(observation_path).iter_batches(batch_size=64, use_threads=False):
        for row in batch.to_pylist():
            actual_hash.update(canonical_json(row) + b'\n'); actual_count += 1
    release.require(actual_count == observation_count and actual_hash.digest() == expected_hash.digest(), 'Parquet round-trip mismatch')
    tables = {'conference_observations': None, 'conference_coverage': []}
    from conference_collection import NOTE
    for key in sorted(set(keys)):
        manifest = json.loads(release.get_bytes(store, key)); task = manifest['task']
        tables['conference_coverage'].append({'source_manifest': key, 'mode': task['mode'],
            'window_start': task['window']['start'], 'window_end_exclusive': task['window']['end'],
            'date_filter': task['scope']['date_filter'], 'coverage_note': NOTE, 'records': manifest['record_count']})
    identity = digest({'version': 'conference-athena-streaming-2.0', 'arrow': pa.__version__, 'inputs': inputs,
        'schema': SCHEMAS, 'config': config, 'bucket': settings.s3_bucket, 'prefix': settings.s3_prefix})
    root = Path(output_root) / identity; root.mkdir(parents=True, exist_ok=True)
    prefix = config['curated_prefix'] + '/' + identity
    files, ddl = {}, []
    for name, rows in tables.items():
        relative = f'tables/{name}/part-00000.parquet'; path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if name == 'conference_observations':
            observation_path.replace(path)
            row_count = observation_count
        else:
            table = pa.Table.from_pylist(rows, schema=pa.schema([(n, release.ARROW_TYPES[t]) for n, t in SCHEMAS[name]]))
            pq.write_table(table, path, compression='snappy', version='1.0')
            release.require(pq.ParquetFile(path).read().equals(table), 'Parquet round-trip mismatch')
            row_count = len(rows)
        from streaming_release import file_digest
        checksum, size = file_digest(path)
        location = f's3://{settings.s3_bucket}/{settings.s3_prefix}/{prefix}/tables/{name}/'
        files[name] = {'path': relative, 'sha256': checksum, 'bytes': size,
                       'rows': row_count, 'location': location, 'columns': SCHEMAS[name]}
        columns = ', '.join(f'{n} {t}' for n, t in SCHEMAS[name])
        ddl.append(f"CREATE EXTERNAL TABLE {config['database']}.{name} ({columns}) STORED AS PARQUET LOCATION '{location}';")
    query = ' UNION ALL '.join(f"SELECT '{n}' AS table_name, count(*) AS records FROM {config['database']}.{n}" for n in sorted(tables)) + ' ORDER BY table_name'
    report = {'streaming_upload': True, 'schema_version': '1.0', 'catalog_owner': 'conferences', 'release_id': identity,
        'release_prefix': prefix, 'bucket': settings.s3_bucket, 's3_prefix': settings.s3_prefix,
        'config': config, 'inputs': inputs, 'universe_hash': digest(universe), 'files': files,
        'queries': {'table_counts': query}, 'expected_results': {'table_counts': [[n, str(files[n]['rows'])] for n in sorted(tables)]},
        'status': 'locally_validated'}
    (root / 'release.json').write_bytes(canonical_json(report) + b'\n')
    (root / 'tables.sql').write_text('\n'.join(ddl) + '\n')
    (root / 'queries.sql').write_text(query + ';\n')
    stage.rmdir()
    return root


def main():
    with (ROOT / '.conference-athena.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 2
        settings = StorageSettings.load(ROOT / 'config/collection-storage.s3.json')
        result = publish_pending(settings.store(), settings, 'conferences',
            load_json(ROOT / 'config/conference-athena.json'), prepare, ROOT / 'conference-athena-build', 1)
        print(json.dumps(result), flush=True)
        return int(result['status'] == 'failed')


if __name__ == '__main__':
    raise SystemExit(main())
