import json,time,boto3
from pathlib import Path
p=Path(__file__).parent;s=boto3.Session(region_name='us-east-1');athena=s.client('athena');bucket='data-collection-059416028963-us-east-1-an'
key='research-data/manifests/collection_runs/source=usda_fas_production_supply_and_distribution/dataset=specialist_inputs/run_443f07f1-b815-4a03-9f8a-0ffa0a5f8193/final.json';m=json.loads(s.client('s3').get_object(Bucket=bucket,Key=key)['Body'].read());paths=['s3://'+bucket+'/research-data/'+b['key']for page in m['pages']for b in page['batches']]
quoted=','.join("'"+x.replace("'","''")+"'"for x in paths)
sql='SELECT count(*) AS rows, count(DISTINCT json_extract_scalar(record_json,\'$.observation_id\')) AS distinct_observations FROM optima_collected_data.committed_records WHERE source=\'usda_fas_production_supply_and_distribution\' AND dataset=\'specialist_inputs\' AND "$path" IN ('+quoted+')'
q=athena.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];out={'query_id':q,'expected':m['record_count'],'sql':sql}
for _ in range(60):
 d=athena.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=d['Status']['State']
 if state in ('SUCCEEDED','FAILED','CANCELLED'):
  out.update(state=state,reason=d['Status'].get('StateChangeReason'),bytes_scanned=d['Statistics'].get('DataScannedInBytes'))
  if state=='SUCCEEDED':out['results']=athena.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
  break
 time.sleep(1)
else:
 athena.stop_query_execution(QueryExecutionId=q);out['state']='CANCELLED_BY_CHECK_TIMEOUT'
(p/'usda-athena-verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
