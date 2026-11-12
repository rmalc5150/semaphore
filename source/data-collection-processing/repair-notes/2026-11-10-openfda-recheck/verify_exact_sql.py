import json,time,boto3
from pathlib import Path
from constellation.control import Control
p=Path(__file__).parent;a=boto3.client('athena',region_name='us-east-1')
sql="""SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM \"AwsDataCatalog\".\"optima_metadata_engine\".\"source_observations\" WHERE source_key = 'fda_openfda' GROUP BY source_key;"""
q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];out={'query_id':q,'sql':sql,'region':'us-east-1','workgroup':'optima-collected-data','account':boto3.client('sts').get_caller_identity()['Account']}
for _ in range(60):
 e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
 if state in ('SUCCEEDED','FAILED','CANCELLED'):
  out.update(state=state,reason=e['Status'].get('StateChangeReason'),statistics=e['Statistics'])
  if state=='SUCCEEDED':out['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
  break
 time.sleep(1)
(p/'exact-athena-query.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
assert state=='SUCCEEDED' and len(out['rows'])>1
c=Control();controls={'daily_allowed':c.daily_allowed(),'historical_allowed':c.allowed()};(p/'collection-controls.json').write_text(json.dumps(controls,indent=2));print(controls)
