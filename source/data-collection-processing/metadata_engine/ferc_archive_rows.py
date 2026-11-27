"""Run row-level FERC metadata labelling in bounded Athena partitions."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time

import boto3

from metadata_engine.archive_native_rows import claim, contract, plan, s3_key
from metadata_engine.controller import publish
from metadata_engine.runtime_db import Database, fingerprint
from metadata_engine.temporary_archives import check_object
from temporary_archive_intake import put_json
from temporary_archive_stage import BUCKET, CONTROL, REGION

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.1.0-ferc-archive-rows'
TABLES = {'contracts': ('contract_unique_id','contract_execution_date'),
          'transactions': ('transaction_unique_id','trade_date')}
OFFICIAL = {
    'official_contracts':('contract_unique_id','contract_execution_date','electricity_contract'),
    'official_transactions':('transaction_unique_id','trade_date','electricity_transaction'),
    'official_ident':('filer_unique_id',None,'electricity_filing_identification'),
    'official_indexpub':('filer_unique_id',None,'electricity_index_publication'),
}


def literal(value):
    return "'" + value.replace("'", "''") + "'"


def sql(job, output):
    if job['official']:
        return official_sql(job,output)
    category = job['dataset']
    raw = job['raw']
    ident, day = TABLES[category]
    columns = [column for column, _ in job['schema']]
    if any(not re.fullmatch(r'[a-z][a-z0-9_]*', column) for column in columns):
        raise ValueError('ferc_metadata_unexpected_column_name')
    raw_values = ','.join(f'CAST("{column}" AS varchar)' for column in columns)
    # Persist provider identity and temporal/measurement labels. Detailed prices,
    # quantities and party fields remain in the checksum-matched source row.
    fields = {
        'native_record_id': 'native_id',
        'seller_company_id_ferc': 'seller_id',
        'reporting_quarter': 'quarter',
        'native_event_date': 'event_day',
        'native_event_date_basis': literal(day),
        'product_name': 'product',
        'rate_units': 'units',
        'provider_release': literal(job['ferc']),
        'availability_basis': literal('unknown'),
        'point_in_time_eligible': literal('false'),
        'native_row_sha256': 'row_hash',
        'duplicate_occurrence': 'CAST(occurrence AS varchar)',
    }
    keys = ','.join(map(literal, fields.keys()))
    vals = ','.join(fields.values())
    common = f"""
    WITH source_rows AS (
        SELECT CAST({ident} AS varchar) AS native_id, CAST({day} AS varchar) AS event_day,
               CAST(seller_company_id_ferc AS varchar) AS seller_id, CAST(product_name AS varchar) AS product,
               CAST(rate_units AS varchar) AS units, {literal(job['quarter'])} AS quarter,
               lower(to_hex(sha256(to_utf8(json_format(CAST(ARRAY[{raw_values}] AS JSON)))))) AS row_hash
        FROM optima_collected_data.archive_ferc_{category}
        WHERE publisher_release={literal(job['ferc'])} AND reporting_quarter={literal(job['quarter'])}
          AND "$path"={literal(raw['s3_uri'])}
    ), native_keys AS (
        SELECT *, json_format(CAST(ARRAY[quarter,seller_id,coalesce(native_id,row_hash)] AS JSON)) AS source_id
        FROM source_rows
    ), indexed AS (
        SELECT *, row_number() OVER(PARTITION BY source_id,row_hash ORDER BY source_id) AS occurrence
        FROM native_keys
    ), identities AS (
        SELECT *, concat('rec_',lower(to_hex(sha256(to_utf8(json_format(CAST(
                ARRAY['record-v1',{literal(job['source'])},{literal(category)},source_id] AS JSON))))))) AS rid,
         json_format(CAST(map(ARRAY[{keys}],ARRAY[{vals}]) AS JSON)) AS labels
        FROM indexed
    )
    SELECT rid AS record_id,
           concat('obs_',lower(to_hex(sha256(to_utf8(json_format(CAST(
                   ARRAY[rid,{literal(raw['sha256'])},row_hash,CAST(occurrence AS varchar)] AS JSON))))))) AS observation_id,
           CAST(NULL AS varchar) AS source_observation_id,
           {literal(job['source'])} AS source_key, {literal(category)} AS dataset,
           {literal('electricity_contract' if category=='contracts' else 'electricity_transaction')} AS record_kind,
           source_id AS source_record_id, {literal(VERSION)} AS contract_version,
           {literal(raw['s3_uri'])} AS raw_s3_uri, {literal(raw['sha256'])} AS raw_sha256,
           'complete' AS raw_completeness_status, 'unresolved' AS entity_match_status,
           {literal(raw['retrieved_at'])} AS ingested_at,
           to_iso8601(current_timestamp) AS labelled_at, labels AS labelled_json
    FROM identities
    """
    return f"UNLOAD ({common}) TO {literal(output)} WITH (format='PARQUET', compression='ZSTD')"


def official_sql(job,output):
    table=job['dataset']
    native_id,event_date,record_kind=OFFICIAL[table]
    raw=job['raw']
    columns={name for name,_ in job['schema']}
    fields={
        'native_record_id':native_id,'filing_package':'filing_package','filing_member':'filing_member',
        'native_row':'CAST(native_row AS varchar)','archive_quarter':literal('2016q1'),
        'availability_basis':literal('unknown'),
    }
    if event_date:
        fields.update(native_event_date=event_date,native_event_date_basis=literal(event_date))
    fields.update((field,field) for field in ('product_name','rate_units','filing_quarter') if field in columns)
    keys=','.join(map(literal,fields))
    values=','.join(fields.values())
    select=f"""
    WITH identified AS (
        SELECT json_format(CAST(ARRAY[filing_package,filing_member,CAST(native_row AS varchar)] AS JSON)) AS source_id,
               json_format(CAST(map(ARRAY[{keys}],ARRAY[{values}]) AS JSON)) AS labels
        FROM optima_collected_data.archive_ferc_{table}
        WHERE archive_sha256={literal(raw['sha256'])} AND native_chunk={literal(job['chunk'])}
          AND "$path"={literal(job['input']['s3_uri'])}
    ), labelled AS (
        SELECT *, concat('rec_',lower(to_hex(sha256(to_utf8(json_format(CAST(
            ARRAY['record-v1',{literal(job['source'])},{literal(table)},source_id] AS JSON))))))) AS rid
        FROM identified
    )
    SELECT rid AS record_id,
           concat('obs_',lower(to_hex(sha256(to_utf8(json_format(CAST(
               ARRAY[rid,{literal(raw['sha256'])},labels] AS JSON))))))) AS observation_id,
           CAST(NULL AS varchar) AS source_observation_id,
           {literal(job['source'])} AS source_key,{literal(table)} AS dataset,
           {literal(record_kind)} AS record_kind,source_id AS source_record_id,
           {literal(VERSION)} AS contract_version,{literal(raw['s3_uri'])} AS raw_s3_uri,
           {literal(raw['sha256'])} AS raw_sha256,'complete' AS raw_completeness_status,
           'unresolved' AS entity_match_status,{literal(raw['retrieved_at'])} AS ingested_at,
           to_iso8601(current_timestamp) AS labelled_at,labels AS labelled_json FROM labelled
    """
    return f"UNLOAD ({select}) TO {literal(output)} WITH (format='PARQUET', compression='ZSTD')"


def unload(athena, job, output, config):
    for attempt in range(3):
        directory = f'{output}attempt-{attempt}/'
        q = athena.start_query_execution(
            QueryString=sql(job,directory), WorkGroup=config['athena_workgroup'],
            ClientRequestToken=fingerprint([job['job_id'],VERSION,directory]),
        )['QueryExecutionId']
        print(json.dumps({'started_query':q,'quarter':job['quarter'],'dataset':job['dataset'],'rows':job['rows']}),flush=True)
        while True:
            result = athena.get_query_execution(QueryExecutionId=q)['QueryExecution']
            state = result['Status']['State']
            if state in ('SUCCEEDED','FAILED','CANCELLED'):
                break
            time.sleep(2)
        if state=='SUCCEEDED':
            rows = [r['Data'][0].get('VarCharValue') for page in athena.get_paginator('get_query_results').paginate(
                QueryExecutionId=q,QueryResultType='DATA_MANIFEST') for r in page['ResultSet']['Rows']]
            files = [name for name in rows if name and name.startswith(directory)]
            if not files:
                raise ValueError('ferc_metadata_unload_has_no_parquet')
            return q, files[0], result['Statistics']
        reason = result['Status'].get('StateChangeReason',state)
        if not result['Status'].get('AthenaError',{}).get('Retryable'):
            raise RuntimeError(f'{q}: {reason}')
    raise RuntimeError(f'ferc_metadata_unload_retries_exhausted:{q}: {reason}')


def publish_one(db, job):
    deadline = time.monotonic()+180
    while time.monotonic() < deadline:
        with db.tx() as cursor:
            cursor.execute("""SELECT s3_uri FROM publication_releases
                WHERE release_id=UNHEX(SUBSTRING(%s,1,32)) AND status='published'""",(job['job_id'],))
            release = cursor.fetchone()
        if release:
            return release['s3_uri']
        publish(db, source_key=job['source'], job_ids=[job['job_id']])
        time.sleep(2)
    raise RuntimeError('ferc_metadata_publication_slots_busy:'+job['job_id'])


def process(session, config, job, publish_labels):
    db = Database(config, session)
    s3, athena = (session.client(name) for name in ('s3','athena'))
    raw = job['raw']
    stored = check_object(s3, BUCKET, s3_key(raw['s3_uri']), raw['sha256'], raw['bytes'])
    if job['official']:
        artifact=job['input']
        stored=check_object(s3,BUCKET,s3_key(artifact['s3_uri']),artifact['sha256'],artifact['bytes'])
    policy = {**contract(job['source']),'contract_version':VERSION,'adapter_version':VERSION,
              'record_kind':'electricity_market_observation'}
    entry, acquired = claim(db,job,policy,stored['ETag'])
    if acquired:
        base = f"{config['prefix']}/jobs/{job['job_id']}"
        folder = f's3://{BUCKET}/{base}/columnar/'
        try:
            q, output, stats = unload(athena,job,folder,config)
            report = put_json(s3,f"{base}/attempts/{entry['lease_token']}.json",{
                'job_id':job['job_id'], 'status':'accepted', 'source':job['source'],'dataset':job['dataset'],
                'quarter':job['quarter'],'records':job['rows'],'raw':raw,'output_uri':output,'athena_unload':q,
                'checked_at':datetime.now(timezone.utc).isoformat(),
                'data_scanned_bytes':stats.get('DataScannedInBytes',0),'graph_write':'omitted_for_bulk_archive_rows',
            })
            db.finish(entry,'accepted',report=report['s3_uri'],output=output,rows=job['rows'])
        except Exception as error:
            db.finish(entry,'uncommitted',(type(error).__name__+':'+str(error))[:500])
            raise
    else:
        output = entry['output_uri']
    proof = publish_one(db,job) if publish_labels else None
    return {'job_id':job['job_id'],'quarter':job['quarter'],'dataset':job['dataset'],'chunk':job['chunk'],'rows':job['rows'],
            'output':output,'publication':proof}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt')
    parser.add_argument('--quarter',action='append')
    parser.add_argument('--dataset',choices=set(TABLES)|set(OFFICIAL))
    parser.add_argument('--official',action='store_true')
    parser.add_argument('--workers',type=int,choices=(1,2,3),default=1)
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--skip-python-canary',action='store_true')
    args=parser.parse_args()
    config=json.loads((ROOT/'config/metadata-engine.json').read_text())
    session=boto3.Session(region_name=REGION)
    jobs=[{**job,'job_id':fingerprint([job['job_id'],VERSION])} for job in plan(session.client('s3'),[args.receipt])
          if (job['official'] if args.official else job['ferc'])
          and (not args.quarter or job['quarter'] in args.quarter)
          and (not args.dataset or job['dataset']==args.dataset)
          and not (args.skip_python_canary and job['quarter']=='2016q1' and job['dataset']=='contracts')]
    if not jobs:
        parser.error('no approved FERC quarter matches the request')
    accepted, failures=[], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        tasks={pool.submit(process,boto3.Session(region_name=REGION),config,job,args.publish):job for job in jobs}
        for task in as_completed(tasks):
            try:
                outcome=task.result()
            except Exception as error:
                job=tasks[task]
                issue={'job_id':job['job_id'],'quarter':job['quarter'],'dataset':job['dataset'],'error':str(error)}
                failures.append(issue)
                print(json.dumps({'failed':issue}),flush=True)
            else:
                accepted.append(outcome)
                print(json.dumps({'accepted':outcome}),flush=True)
    report={'version':VERSION,'accepted':sorted(accepted,key=lambda job:job['job_id']),
            'failures':sorted(failures,key=lambda job:job['job_id']),'rows':sum(j['rows'] for j in accepted)}
    result=put_json(session.client('s3'),f'{CONTROL}/row-metadata/ferc-{fingerprint(report)}.json',report)
    print(json.dumps({'receipt':result['s3_uri'],'jobs':len(accepted),'rows':report['rows'],'failures':len(failures)}),flush=True)
    return int(bool(failures))


if __name__=='__main__':
    raise SystemExit(main())
