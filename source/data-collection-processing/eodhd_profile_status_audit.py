"""Aggregate catalogue outcomes in bounded Athena partition scans; save to S3."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import time
import boto3


def main():
    glue = boto3.client('glue', region_name='us-east-1')
    athena = boto3.client('athena', region_name='us-east-1')
    parts = [p['Values'][0] for page in glue.get_paginator('get_partitions').paginate(
        DatabaseName='optima_eodhd_research', TableName='source_observations_windows') for p in page['Partitions']]
    def query(window):
        sql = "SELECT coalesce(json_extract_scalar(payload_json,'$.profile_status'),'available') AS profile_status,count(*) AS records,count_if(coalesce(json_extract_scalar(payload_json,'$.general.Description'),'')='') AS missing_description FROM source_observations_windows WHERE window_id='" + window + "' GROUP BY 1"
        q = athena.start_query_execution(QueryString=sql, QueryExecutionContext={'Database':'optima_eodhd_research'}, WorkGroup='optima-eodhd-research')['QueryExecutionId']
        while True:
            result = athena.get_query_execution(QueryExecutionId=q)['QueryExecution']
            state = result['Status']['State']
            if state == 'SUCCEEDED':
                rows = [[c.get('VarCharValue') for c in r['Data']] for r in athena.get_query_results(QueryExecutionId=q)['ResultSet']['Rows'][1:]]
                return {'window_id':window,'query_id':q,'rows':rows,'bytes_scanned':result['Statistics']['DataScannedInBytes']}
            if state in {'FAILED','CANCELLED'}:
                return {'window_id':window,'query_id':q,'error':result['Status'].get('StateChangeReason',state)}
            time.sleep(0.5)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(query, parts))
    totals = {}
    for result in results:
        for status, count, missing in result.get('rows',[]):
            group = totals.setdefault(status, {'records':0,'missing_description':0})
            group['records'] += int(count)
            group['missing_description'] += int(missing)
    report = {'checked_at':datetime.now(timezone.utc).isoformat(),'profile_outcomes':totals,'windows':results}
    s3 = boto3.client('s3',region_name='us-east-1')
    s3.put_object(Bucket='data-collection-059416028963-us-east-1-an',Key='research-data/operations/eodhd/global-audit/2026-10-20/profile-statuses.json',Body=json.dumps(report).encode(),ServerSideEncryption='AES256',ContentType='application/json')
    print(json.dumps({'totals':totals,'failed_windows':[r for r in results if 'error' in r]}),flush=True)


if __name__ == '__main__':
    main()
