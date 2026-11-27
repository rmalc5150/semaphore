"""Publish verified native archive data to Athena from an intake receipt."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import time

import boto3

from committed_data_athena import DB, query
from metadata_engine.temporary_archives import VERSION, check_object
from research_contract import digest
from temporary_archive_intake import exact_bytes, put_json
from temporary_archive_stage import BUCKET, CONTROL, REGION

OWNER = 'temporary-archive-intake-v1'
REGISTRY = 'research-data/athena-committed/temporary-archive-intake'
TABLE_NAMES = {'contracts': 'archive_ferc_contracts', 'transactions': 'archive_ferc_transactions'}


def value(value):
    if not re.fullmatch(r'[a-zA-Z0-9_.-]+', value):
        raise ValueError('invalid_athena_partition_value')
    return f"'{value}'"


def hive_type(arrow_type):
    if match := re.fullmatch(r'dictionary<values=([^,]+), indices=[a-z0-9]+, ordered=[01]>', arrow_type):
        return hive_type(match[1])
    if arrow_type.startswith('timestamp['):
        return 'timestamp'
    return {
        'string': 'string', 'large_string': 'string', 'bool': 'boolean', 'date32[day]': 'date',
        'int64': 'bigint', 'int32': 'int', 'double': 'double', 'float': 'float',
    }[arrow_type]


def columns(schema):
    if any(not re.fullmatch(r'[a-z][a-z0-9_]*', name) for name, _ in schema):
        raise ValueError('unsafe_athena_column_name')
    return [{'Name': name, 'Type': hive_type(arrow_type)} for name, arrow_type in schema]


def descriptor(schema, location):
    return {'Columns': schema, 'Location': location, 'Compressed': True,
            'InputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
            'OutputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
            'SerdeInfo': {'SerializationLibrary': 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'}}


def destination(glue, table, schema, partition_names):
    definition = {'Name': table, 'TableType': 'EXTERNAL_TABLE',
                  'Parameters': {'classification': 'parquet', 'optima_owner': OWNER},
                  'PartitionKeys': [{'Name': name, 'Type': 'string'} for name in partition_names],
                  'StorageDescriptor': descriptor(schema, f's3://{BUCKET}/{REGISTRY}/empty/{table}/')}
    try:
        current = glue.get_table(DatabaseName=DB, Name=table)['Table']
    except glue.exceptions.EntityNotFoundException:
        glue.create_table(DatabaseName=DB, TableInput=definition)
    else:
        if (current['Parameters'].get('optima_owner') != OWNER
                or current['StorageDescriptor']['Columns'] != schema
                or current['PartitionKeys'] != definition['PartitionKeys']):
            raise ValueError('existing_archive_athena_table_contract_mismatch')


def partition(glue, table, schema, keys, uri, sha):
    where = uri.rsplit('/', 1)[0]+'/'
    definition = {'Values': list(keys), 'StorageDescriptor': descriptor(schema, where),
                  'Parameters': {'optima_owner': OWNER, 'source_sha256': sha}}
    try:
        existing = glue.get_partition(DatabaseName=DB, TableName=table, PartitionValues=list(keys))['Partition']
    except glue.exceptions.EntityNotFoundException:
        glue.create_partition(DatabaseName=DB, TableName=table, PartitionInput=definition)
    else:
        if (existing['Parameters'] != definition['Parameters']
                or existing['StorageDescriptor']['Location'] != where):
            raise ValueError('existing_archive_athena_partition_identity_mismatch')


def group(s3, receipt):
    tables = defaultdict(list)
    for object_info in receipt['processed']:
        uri = object_info['processing_manifest']
        prefix = f's3://{BUCKET}/'
        if not uri.startswith(prefix) or not uri.endswith(f'/{VERSION}/manifest.json'):
            raise ValueError('unexpected_archive_processing_manifest')
        result = json.loads(exact_bytes(s3, uri.removeprefix(prefix)))
        source, summary, raw = result['source'], result['summary'], result['raw']
        if source != object_info['source'] or summary != object_info['summary']:
            raise ValueError('archive_intake_receipt_and_manifest_disagree')
        for item in result['tables']:
            artifact = item['object']
            key = artifact['s3_uri'].removeprefix(prefix)
            if key == artifact['s3_uri'] or not key.startswith('research-data/'):
                raise ValueError('unexpected_archive_parquet_location')
            check_object(s3, BUCKET, key, artifact['sha256'], artifact['bytes'])
            if 'publisher_release' in summary:
                name = TABLE_NAMES[item['dataset']]
                partition_names = ('publisher_release', 'reporting_quarter')
                values = (summary['publisher_release'], summary['period_min'])
            elif summary.get('native_release')=='ferc_official_2016q1':
                name = f"archive_ferc_{item['dataset']}"
                partition_names = ('archive_sha256', 'native_chunk')
                values = (raw['sha256'], item['partition_id'])
            else:
                name = 'archive_native_rows'
                partition_names = ('source_key', 'dataset_key', 'archive_sha256')
                values = (source, item['dataset'], raw['sha256'])
            for content in values:
                value(content)
            tables[name].append((partition_names, values, columns(item['schema']), artifact, item['rows']))
    return tables


def verify_table(athena, table, partition_names, entries):
    # Select only the new immutable partitions and compare exact row counts.
    grouped = defaultdict(list)
    for _, keys, _, _, rows in entries:
        grouped[keys[:-1]].append((keys[-1], rows))
    results = []
    for leading, entries_in_group in sorted(grouped.items()):
        coarse = [f'{field}={value(val)}' for field, val in zip(partition_names[:-1], leading)]
        tail = ','.join(value(key) for key, _ in entries_in_group)
        predicate = ' AND '.join([*coarse, f'{partition_names[-1]} IN ({tail})'])
        q = query(athena, f'SELECT {partition_names[-1]}, count(*) FROM {DB}.{table} '
                          f'WHERE {predicate} GROUP BY {partition_names[-1]}')
        expected = {key: str(rows) for key, rows in entries_in_group}
        if dict(q['rows']) != expected:
            raise ValueError(f'athena_archive_counts_mismatch:{table}:{q["query_id"]}')
        results.append({'scope': list(leading), 'query_id': q['query_id'], 'bytes_scanned': q['bytes_scanned'],
                        'partitions': len(expected), 'rows': sum(int(count) for count in expected.values())})
    return results


def publish_metadata(session, receipt):
    from metadata_engine.controller import publish
    from metadata_engine.runtime_db import Database
    from research_contract import load_json

    jobs = defaultdict(list)
    for item in receipt['processed']:
        job = item['metadata_job_id']
        if not re.fullmatch(r'[a-f0-9]{64}', job):
            raise ValueError('invalid_archive_metadata_job_id')
        jobs[item['source']].append(job)
    config = load_json(Path(__file__).resolve().parent/'config/metadata-engine.json')
    db = Database(config, session=session)
    all_ids = [job for ids in jobs.values() for job in ids]
    deadline = time.monotonic()+120
    while True:
        published = {row['job_id'] for row in metadata_publications(db, all_ids)}
        if published == set(all_ids):
            break
        for source, ids in sorted(jobs.items()):
            pending = [job for job in ids if job not in published]
            for offset in range(0, len(pending), 5):
                publish(db, source_key=source, job_ids=pending[offset:offset+5])
        if time.monotonic() >= deadline:
            break
        time.sleep(2)
    return verify_metadata(session, receipt)


def metadata_publications(db, ids):
    arguments = ','.join(['%s']*len(ids))
    with db.tx() as cursor:
        cursor.execute(f"""SELECT j.job_id,j.source_key,j.state,j.output_uri,j.output_rows,
                           p.s3_uri,p.manifest_sha256 FROM engine_jobs j
                           JOIN publication_releases p ON p.release_id=UNHEX(SUBSTRING(j.job_id,1,32))
                           WHERE j.job_id IN ({arguments}) AND p.status='published'""", list(ids))
        return cursor.fetchall()


def verify_metadata(session, receipt):
    from metadata_engine.runtime_db import Database, fingerprint
    from research_contract import load_json

    config = load_json(Path(__file__).resolve().parent/'config/metadata-engine.json')
    db = Database(config, session=session)
    expected = {item['metadata_job_id']: item['source'] for item in receipt['processed']}
    rows = metadata_publications(db, expected)
    if {row['job_id']: row['source_key'] for row in rows} != expected:
        raise ValueError('athena_metadata_publication_receipts_missing')

    glue = session.client('glue')
    table = 'source_observations'
    parts = {}
    ids = sorted(expected)
    for offset in range(0, len(ids), 100):
        response = glue.batch_get_partition(DatabaseName=config['athena_database'], TableName=table,
                    PartitionsToGet=[{'Values': [job]} for job in ids[offset:offset+100]])
        for part in response['Partitions']:
            parts[part['Values'][0]] = part['StorageDescriptor']['Location']
    if set(parts) != set(expected):
        raise ValueError('athena_metadata_partitions_missing')

    s3 = session.client('s3')
    def readback(row):
        prefix = f's3://{BUCKET}/'
        if not row['s3_uri'].startswith(prefix):
            raise ValueError('unexpected_athena_metadata_receipt_path')
        record = json.loads(exact_bytes(s3, row['s3_uri'].removeprefix(prefix)))
        if (fingerprint(record) != row['manifest_sha256']
                or row['state'] != 'accepted' or row['output_rows'] != 1
                or record['job_id'] != row['job_id'] or record['status'] != 'verified'
                or record['rows'] != 1 or record['output_uri'] != row['output_uri']
                or parts[row['job_id']] != row['output_uri'].rsplit('/', 1)[0]+'/'):
            raise ValueError('athena_metadata_release_readback_mismatch')
        return record['query_execution_id']

    with ThreadPoolExecutor(max_workers=6) as executor:
        queries = sorted(set(executor.map(readback, rows)))
    return {'table': f"{config['athena_database']}.{table}",
            'records': len(rows), 'by_source': dict(Counter(expected.values())), 'queries': queries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', help='Verified S3 intake receipt URI')
    parser.add_argument('--metadata', action='store_true', help='Publish and verify the exact accepted metadata jobs')
    args = parser.parse_args()
    prefix = f's3://{BUCKET}/{CONTROL}/runs/'
    if not args.receipt.startswith(prefix) or not re.fullmatch(r'[a-f0-9]{64}\.json', args.receipt.removeprefix(prefix)):
        parser.error('expected an archive intake receipt S3 URI')
    session = boto3.Session(region_name=REGION)
    s3, glue, athena = (session.client(service) for service in ('s3', 'glue', 'athena'))
    document = json.loads(exact_bytes(s3, args.receipt.removeprefix(f's3://{BUCKET}/')))
    groups = group(s3, document)
    outputs = {}
    for table, entries in sorted(groups.items()):
        fields, _, schema, _, _ = entries[0]
        if any(names != fields or cols != schema for names, _, cols, _, _ in entries):
            raise ValueError('inconsistent_archive_partition_schemas')
        destination(glue, table, schema, fields)
        for _, values, _, artifact, _ in entries:
            partition(glue, table, schema, values, artifact['s3_uri'], artifact['sha256'])
        outputs[table] = verify_table(athena, table, fields, entries)
        print(json.dumps({'table': f'{DB}.{table}', 'verification': outputs[table]}), flush=True)
    sha = args.receipt.removeprefix(prefix).removesuffix('.json')
    report = {'intake': args.receipt, 'database': DB, 'tables': outputs}
    if args.metadata:
        report['metadata'] = publish_metadata(session, document)
        print(json.dumps({'metadata_verification': report['metadata']}), flush=True)
    key = f'{CONTROL}/athena-verifications/{sha}/{digest(report)}.json'
    proof = put_json(s3, key, report)
    print(json.dumps({'verification': proof['s3_uri']}), flush=True)


if __name__ == '__main__':
    main()
