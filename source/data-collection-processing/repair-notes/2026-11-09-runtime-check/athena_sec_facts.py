import json,time,boto3
from pathlib import Path
p=Path(__file__).parent;a=boto3.client('athena',region_name='us-east-1');sql="SELECT source_key,count(*) AS observations,count(DISTINCT raw_s3_uri) AS linked_raw_objects,count_if(raw_completeness_status='complete') AS complete_raw_observations,min(ingested_at) AS first_ingested_at,max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key='sec_companyfacts' GROUP BY source_key"
q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];out={'query_id':q,'sql':sql}
for _ in range(60):
 r=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=r['Status']['State']
 if state in ('SUCCEEDED','FAILED','CANCELLED'):
  out.update(state=state,bytes_scanned=r['Statistics'].get('DataScannedInBytes'),reason=r['Status'].get('StateChangeReason'))
  if state=='SUCCEEDED':out['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
  break
 time.sleep(1)
else:a.stop_query_execution(QueryExecutionId=q);out['state']='CANCELLED_BY_TIMEOUT'
(p/'sec-companyfacts-athena.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
