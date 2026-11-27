"""Label each verified native archive row with the standard metadata engine."""
import argparse
from datetime import date
import fcntl
import hashlib
import json
from pathlib import Path
import re
import tempfile
import uuid

import boto3
import pyarrow as pa
import pyarrow.parquet as pq

from metadata_engine.controller import COLUMNS
from metadata_engine.labelling import label_observation
from metadata_engine.runtime_db import Database, encoded, fingerprint
from metadata_engine.temporary_archives import check_object
from temporary_archive_intake import exact_bytes, put_checked, put_json
from temporary_archive_stage import BUCKET, CONTROL, REGION

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0.0-archive-rows'
FORMAT = 'archive_parquet_rows'
SCHEMA = pa.schema([(name, pa.string()) for name, _ in COLUMNS])
KINDS = {
    123: 'energy_asset', 189: 'product_safety_alert', 235: 'surveillance_observation',
    254: 'regulatory_notice',
    255: 'director_transaction_notification', 256: 'investment_holding', 266: 'electricity_filing',
}
MISSING = ('404', 'NotFound', 'NoSuchKey')


def s3_key(uri):
    prefix = f's3://{BUCKET}/'
    if not uri.startswith(prefix+'research-data/'):
        raise ValueError('archive_row_input_outside_project')
    return uri.removeprefix(prefix)


def plan(s3, receipt_keys):
    jobs = {}
    for key in receipt_keys:
        if not re.fullmatch(re.escape(CONTROL)+r'/runs/[a-f0-9]{64}\.json', key):
            raise ValueError('invalid_archive_intake_receipt_key')
        body = json.loads(exact_bytes(s3, key))
        if body['errors'] or not body['processed']:
            raise ValueError('archive_row_plan_requires_completed_intake')
        for item in body['processed']:
            manifest_key = s3_key(item['processing_manifest'])
            manifest = json.loads(exact_bytes(s3, manifest_key))
            if manifest['source'] != item['source'] or manifest['summary'] != item['summary']:
                raise ValueError('archive_row_processing_manifest_mismatch')
            for table in manifest['tables']:
                identity = fingerprint([manifest_key, table['dataset'], table['object']['sha256'], VERSION])
                jobs[identity] = {'job_id': identity, 'source': manifest['source'],
                                  'raw': manifest['raw'], 'input': table['object'],
                                  'dataset': table['dataset'], 'rows': table['rows'], 'schema': table['schema'],
                                  'official': manifest['summary'].get('native_release'),
                                  'chunk': table.get('partition_id'),
                                  'periods': table.get('periods', {}), 'ferc': manifest['summary'].get('publisher_release'),
                                  'quarter': manifest['summary'].get('period_min') if 'publisher_release' in manifest['summary'] else None}
    return sorted(jobs.values(), key=lambda t: (bool(t['ferc']), t['source'], t['dataset'], t['quarter'] or ''))


def contract(source):
    return {'source_key': source, 'contract_version': VERSION, 'adapter': FORMAT,
            'adapter_version': VERSION, 'record_kind': KINDS[int(source.rsplit('_', 1)[1])],
            'license_policy_id': 'source-rights-review-required',
            'raw_requirements': {'version': VERSION, 'minimum_completeness': 'complete',
                                 'required_artifact_kinds': ['dataset_file'], 'forbidden_shortcuts': ['archive_summary']}}


def claim(db, job, policy, etag):
    now = str(uuid.uuid4())
    version, adapter = policy['contract_version'], policy['adapter']
    with db.tx() as cursor:
        cursor.execute('SELECT state FROM engine_sources WHERE source_key=%s FOR UPDATE', (job['source'],))
        state = cursor.fetchone()
        if not state or state['state'] != 'enabled':
            raise RuntimeError('archive_row_metadata_source_is_not_enabled')
        cursor.execute('INSERT IGNORE INTO source_contracts VALUES(%s,%s,%s,%s,%s,UTC_TIMESTAMP(6))',
                       (job['source'], version, adapter, encoded(policy), fingerprint(policy)))
        cursor.execute('SELECT contract_sha256 FROM source_contracts WHERE source_key=%s AND contract_version=%s',
                       (job['source'], version))
        if cursor.fetchone()['contract_sha256'] != fingerprint(policy):
            raise RuntimeError('archive_row_metadata_contract_conflict')
        cursor.execute('INSERT IGNORE INTO source_raw_requirements VALUES(%s,%s,%s,%s,%s,%s)',
                       (job['source'], version, version, 'complete', '["dataset_file"]', '["archive_summary"]'))
        cursor.execute("""INSERT IGNORE INTO engine_jobs
            (job_id,source_key,input_key,input_etag,input_format,contract_version,priority,state,available_after,created_at)
            VALUES(%s,%s,%s,%s,%s,%s,40,'uncommitted',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))""",
                       (job['job_id'],job['source'],s3_key(job['input']['s3_uri']),etag,adapter,version))
        cursor.execute('SELECT *,lease_until>=UTC_TIMESTAMP(6) AS active_lease FROM engine_jobs WHERE job_id=%s FOR UPDATE',
                       (job['job_id'],))
        entry = cursor.fetchone()
        if entry['state']=='accepted':
            if entry['output_rows'] != job['rows']:
                raise ValueError('archive_row_metadata_count_changed')
            return entry, False
        if entry['state']=='running' and entry['active_lease']:
            raise RuntimeError('archive_row_metadata_job_already_leased')
        cursor.execute("""UPDATE engine_jobs SET state='running',lease_token=%s,lease_until=DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 30 MINUTE),
                       attempts=attempts+1 WHERE job_id=%s""",(now,job['job_id']))
        entry['lease_token'] = now
        return entry, True


def row_record(job, row, native, raw_artifact):
    period, basis = row['period'], row['period_basis']
    dt = None
    if period and re.fullmatch(r'\d{4}-\d\d-\d\d', period):
        date.fromisoformat(period)
        dt = {'value': period, 'precision': 'day'}
    event = dt if basis in ('alert_publication_date','holdings_snapshot_date','notification_date','filing_date',
                              'contract_execution_date','trade_date') else None
    published = dt if basis=='alert_publication_date' else None
    if basis=='notice_publication_timestamp':
        published = {'value':period,'precision':'second'}
    elif basis=='notice_filing_timestamp':
        event = {'value':period,'precision':'second'}
    locator = {'member': row['source_member'], 'row': row['native_row'],
               'provider_id': row['native_id'], 'parsed_artifact_sha256': job['input']['sha256']}
    source_id = row['native_id'] or fingerprint([row['source_member'], row['native_row']])
    return {
        'source': job['source'], 'dataset': job['dataset'], 'source_record_id': source_id,
        'source_record_id_basis': 'provider' if row['native_id'] else 'archive_member_and_row',
        'raw_s3_uri': raw_artifact['s3_uri'], 'raw_sha256': raw_artifact['sha256'],
        'raw_completeness_status': 'complete', 'raw_artifacts': [raw_artifact],
        'source_url': job['raw']['source_url'], 'evidence_locator': locator,
        'event_at': event, 'source_published_at': published,
        'available_at': None, 'availability_basis': 'unknown',
        'ingested_at': job['raw']['retrieved_at'], 'parser_version': VERSION,
        'payload': {'data': native, 'native_period': period, 'native_period_basis': basis},
    }


def records(reader, job):
    if not job['ferc']:
        for batch in reader.iter_batches(batch_size=2048):
            yield [(row, json.loads(row['native_json'])) for row in batch.to_pylist()]
        return
    category = job['dataset']
    id_field = 'transaction_unique_id' if category=='transactions' else 'contract_unique_id'
    date_field = 'trade_date' if category=='transactions' else 'contract_execution_date'
    columns = [id_field, date_field, 'seller_company_id_ferc', 'year_quarter', 'product_name']
    position = 0
    for batch in reader.iter_batches(batch_size=8192, columns=columns):
        result = []
        for native in batch.to_pylist():
            position += 1
            day = native[date_field]
            if day:
                native[date_field] = day.isoformat()
            key = native[id_field]
            provider = '|'.join(str(native[k]) for k in ('year_quarter','seller_company_id_ferc',id_field)) if key else None
            row = {'native_id': provider, 'native_row': position,
                   'source_member': job['input']['s3_uri'].rsplit('/',1)[-1],
                   'period': native[date_field] or job['quarter'],
                   'period_basis': date_field if day else 'reporting_quarter'}
            result.append((row,native))
        yield result


def process(s3, db, job, scratch):
    raw = job['raw']
    inputs = job['input']
    source = check_object(s3, BUCKET, s3_key(raw['s3_uri']), raw['sha256'], raw['bytes'])
    stored = check_object(s3, BUCKET, s3_key(inputs['s3_uri']), inputs['sha256'], inputs['bytes'])
    policy = contract(job['source'])
    entry, acquired = claim(db, job, policy, stored['ETag'])
    if not acquired:
        return {**job, 'output': entry['output_uri']}
    base = f"{db.config['prefix']}/jobs/{job['job_id']}"
    artifact = {key: raw[key] for key in ('s3_uri','sha256','bytes','source_url')}
    artifact.update(origin='first_party_source', artifact_kind='dataset_file', media_type=source.get('ContentType'))
    try:
        with tempfile.TemporaryDirectory(dir=scratch) as temporary:
            input_path, output_path = (Path(temporary)/name for name in ('in.parquet','out.parquet'))
            s3.download_file(BUCKET, s3_key(inputs['s3_uri']), str(input_path))
            with input_path.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != inputs['sha256']:
                    raise ValueError('archive_row_parquet_checksum_mismatch')
            reader = pq.ParquetFile(input_path)
            if reader.metadata.num_rows != job['rows']:
                raise ValueError('archive_row_input_count_mismatch')
            count = 0
            with pq.ParquetWriter(output_path, SCHEMA, compression='zstd') as writer:
                for batch in records(reader, job):
                    labelled = [label_observation(row_record(job, item, data, artifact), policy,
                                                  labelled_at=raw['retrieved_at']) for item,data in batch]
                    items = [{name: item.get(name) for name,_ in COLUMNS if name!='labelled_json'}
                             | {'labelled_json': encoded(item)} for item in labelled]
                    writer.write_table(pa.Table.from_pylist(items, schema=SCHEMA))
                    count += len(items)
            if count != job['rows'] or pq.ParquetFile(output_path).metadata.num_rows != count:
                raise ValueError('archive_row_label_count_mismatch')
            with output_path.open('rb') as stream:
                sha = hashlib.file_digest(stream,'sha256').hexdigest()
                stream.seek(0)
                output = put_checked(s3, f'{base}/data/{sha}/part.parquet', stream, sha,
                                     output_path.stat().st_size, 'application/vnd.apache.parquet')
        report = put_json(s3, f"{base}/attempts/{entry['lease_token']}.json",
                          {'job_id': job['job_id'], 'status':'accepted', 'source':job['source'],
                           'dataset':job['dataset'], 'records':count, 'input':inputs,
                           'raw':raw, 'output':output, 'graph_write':'omitted_for_bulk_archive_rows'})
        db.finish(entry, 'accepted', report=report['s3_uri'], output=output['s3_uri'], rows=count)
        return {**job,'output':output['s3_uri']}
    except Exception as error:
        db.finish(entry, 'uncommitted', (type(error).__name__+':'+str(error))[:500])
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipts', nargs='+', help='S3 keys for completed archive intake receipts')
    parser.add_argument('--ferc', choices=('skip','canary'), default='skip')
    parser.add_argument('--scratch',type=Path,default=Path('/opt/constellation/tmp'))
    args = parser.parse_args()
    s3 = boto3.client('s3',region_name=REGION)
    db = Database(json.loads((ROOT/'config/metadata-engine.json').read_text()))
    jobs = plan(s3,args.receipts)
    selected = [job for job in jobs if not job['official'] and (not job['ferc'] or (
        args.ferc=='canary' and job['quarter']=='2016q1' and job['dataset']=='contracts'))]
    with (args.scratch/'.metadata-archive-native-rows.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        accepted = []
        for job in selected:
            result = process(s3,db,job,args.scratch)
            accepted.append(result)
            print(json.dumps({'accepted':result['job_id'],'source':result['source'],'dataset':result['dataset'],
                              'rows':result['rows']}),flush=True)
    document = {'contract_version':VERSION,'accepted':accepted,'receipts':args.receipts,
                'rows':sum(job['rows'] for job in accepted),'remaining_rows':sum(job['rows'] for job in jobs)-sum(job['rows'] for job in accepted)}
    ref = put_json(s3,f'{CONTROL}/row-metadata/{fingerprint(document)}.json',document)
    print(json.dumps({'report':ref['s3_uri'],'rows':document['rows'],'remaining_rows':document['remaining_rows']}),flush=True)


if __name__=='__main__':
    main()
