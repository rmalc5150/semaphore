import json,time
from pathlib import Path
import boto3
P=Path(__file__).parent;a=boto3.client('athena',region_name='us-east-1')
queries={
 'counts-before':"SELECT source_key,count(*) observations,count(DISTINCT raw_s3_uri) linked_raw_objects,count_if(raw_completeness_status='complete') complete_raw_observations,min(ingested_at) first_ingested_at,max(ingested_at) latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key='trade_screening' GROUP BY source_key",
 'details-before':"SELECT source_key,source_record_id,record_kind,raw_completeness_status,ingested_at,json_extract_scalar(labelled_json,'$.payload.data.name') name,json_extract_scalar(labelled_json,'$.payload.data.source') provider_list FROM optima_metadata_engine.source_observations WHERE source_key='trade_screening' LIMIT 25",
 'legacy-preview':"SELECT source,dataset,record_id,ingested_at,json_extract_scalar(event_at_json,'$.value') event_date,source_url FROM optima_collected_data.observations WHERE source='trade_screening' AND dataset='specialist_inputs' LIMIT 1"
}
results={}
for name,sql in queries.items():
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];results[name]={'query_id':q,'sql':sql};print(name,q,flush=True)
deadline=time.monotonic()+100
while time.monotonic()<deadline and any('state'not in r for r in results.values()):
 for name,r in results.items():
  if 'state'in r:continue
  e=a.get_query_execution(QueryExecutionId=r['query_id'])['QueryExecution'];state=e['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   r.update(state=state,reason=e['Status'].get('StateChangeReason'),bytes_scanned=e['Statistics'].get('DataScannedInBytes'))
   if state=='SUCCEEDED':r['rows']=a.get_query_results(QueryExecutionId=r['query_id'])['ResultSet']['Rows']
 time.sleep(1)
for name,r in results.items():
 if 'state'not in r:a.stop_query_execution(QueryExecutionId=r['query_id']);r['state']='TIMEOUT'
 (P/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n');print(name,r['state'],[[v.get('VarCharValue')for v in x['Data']]for x in r.get('rows',[])[:4]],flush=True)
