"""Bounded fresh Athena readback of the publication repair and review examples."""
import json, time
from pathlib import Path
import boto3

P = Path(__file__).parent
a = boto3.client('athena', region_name='us-east-1')
sql = (P / 'review-queries.sql').read_text()
statements = [part.strip() for part in sql.split(';\n\n') if part.strip()]
repaired = json.loads((P / 'publication-repair.json').read_text())
ids = [r['job_id'] for r in repaired['verified_publication_rows']]
queries = dict(zip(('counts-after', 'details-after'), statements))
queries['repaired-partitions'] = "SELECT count(*) observations,count(DISTINCT job_id) published_batches,count_if(raw_completeness_status='complete') complete_raw_observations FROM optima_metadata_engine.source_observations WHERE source_key='trade_screening' AND job_id IN (" + ','.join("'" + j + "'" for j in ids) + ')'
results = {}
for name, query in queries.items():
    q = a.start_query_execution(QueryString=query, WorkGroup='optima-collected-data', ResultReuseConfiguration={'ResultReuseByAgeConfiguration': {'Enabled': False}})['QueryExecutionId']
    results[name] = {'query_id': q, 'sql': query}
deadline = time.monotonic() + 100
while time.monotonic() < deadline and any('state' not in r for r in results.values()):
    for r in results.values():
        if 'state' in r:
            continue
        e = a.get_query_execution(QueryExecutionId=r['query_id'])['QueryExecution']
        state = e['Status']['State']
        if state in ('SUCCEEDED', 'FAILED', 'CANCELLED'):
            r.update(state=state, reason=e['Status'].get('StateChangeReason'), bytes_scanned=e['Statistics'].get('DataScannedInBytes'))
            if state == 'SUCCEEDED':
                r['rows'] = a.get_query_results(QueryExecutionId=r['query_id'])['ResultSet']['Rows']
    time.sleep(1)
for name, r in results.items():
    if 'state' not in r:
        a.stop_query_execution(QueryExecutionId=r['query_id'])
        r['state'] = 'TIMEOUT'
    (P / (name + '.json')).write_text(json.dumps(r, indent=2) + '\n')
    print(name, r['query_id'], r['state'], 'data_rows', len(r.get('rows', [])) - 1)
    if name != 'details-after':
        print([[v.get('VarCharValue') for v in x['Data']] for x in r.get('rows', [])])
assert all(r['state'] == 'SUCCEEDED' for r in results.values()), results
values = [v.get('VarCharValue') for v in results['repaired-partitions']['rows'][1]['Data']]
assert values == [str(repaired['repaired_observations']), str(repaired['repaired_batches']), str(repaired['repaired_observations'])], values
assert len(results['details-after']['rows']) == 26
