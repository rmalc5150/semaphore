"""Register and verify Athena access to committed research-feed batches."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import time

from constellation.control import Control
from constellation.research_feeds import KAKEN, OPENALEX, Evidence

DATABASE = 'optima_research_feeds'
SOURCES = (OPENALEX, KAKEN)
COLUMNS = ('source_record_id', 'event_date', 'provider_updated_at', 'source_url',
           'raw_uri', 'collected_at', 'window_id', 'payload_json')


def ddl(source, location):
    schema = ', '.join(f'{field} string' for field in COLUMNS)
    return f"""
        CREATE EXTERNAL TABLE IF NOT EXISTS {DATABASE}.{source} ({schema})
        PARTITIONED BY (collection_mode string)
        ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'
        STORED AS INPUTFORMAT 'org.apache.hadoop.hive.ql.io.SymlinkTextInputFormat'
        OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
        LOCATION '{location}'
        TBLPROPERTIES (
            'projection.enabled' = 'true',
            'projection.collection_mode.type' = 'enum',
            'projection.collection_mode.values' = 'daily,historical',
            'storage.location.template' = '{location}${{collection_mode}}/'
        )
    """


def run(athena, output, sql):
    response = athena.start_query_execution(QueryString=sql, WorkGroup='primary',
                                            ResultConfiguration={'OutputLocation': output})
    identity = response['QueryExecutionId']
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        execution = athena.get_query_execution(QueryExecutionId=identity)['QueryExecution']
        status = execution['Status']
        if status['State'] == 'SUCCEEDED':
            return identity
        if status['State'] in {'FAILED', 'CANCELLED'}:
            raise RuntimeError(f"{identity} {status.get('StateChangeReason', status['State'])}")
        time.sleep(2)
    raise TimeoutError(f'{identity} Athena query is still running')


def verify(athena, output, source, mode):
    query = f"""
        SELECT count(*) AS sample_count, count(DISTINCT source_record_id) AS unique_ids,
               count_if(raw_uri LIKE 's3://%' AND payload_json IS NOT NULL) AS records_with_evidence
        FROM (
            SELECT source_record_id, raw_uri, payload_json
            FROM {DATABASE}.{source}
            WHERE collection_mode = '{mode}'
            LIMIT 100
        )
    """
    identity = run(athena, output, query)
    rows = athena.get_query_results(QueryExecutionId=identity)['ResultSet']['Rows']
    counts = [int(cell['VarCharValue']) for cell in rows[1]['Data']]
    return {'source': source, 'mode': mode, 'query_id': identity,
            **dict(zip(('sample_count', 'unique_ids', 'records_with_evidence'), counts))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('register', 'verify'))
    args = parser.parse_args()
    control = Control()
    athena = control.session.client('athena')
    evidence = Evidence(control)
    output = f's3://{evidence.bucket}/research-data/athena-results/research-feeds/'
    if args.action == 'register':
        database_query = run(athena, output, f'CREATE DATABASE IF NOT EXISTS {DATABASE}')
        tables = {source: run(athena, output, ddl(source, evidence.uri(f'published/{source}/')))
                  for source in SOURCES}
        print(json.dumps({'database': DATABASE, 'database_query': database_query, 'tables': tables}))
    else:
        with ThreadPoolExecutor(max_workers=4) as pool:
            checks = [pool.submit(verify, athena, output, source, mode)
                      for source in SOURCES for mode in ('daily', 'historical')]
            print(json.dumps([check.result() for check in checks]))


if __name__ == '__main__':
    main()
