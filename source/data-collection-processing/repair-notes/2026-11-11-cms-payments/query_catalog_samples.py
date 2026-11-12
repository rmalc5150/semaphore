import boto3,json,time
from pathlib import Path
p=Path(__file__).parent;a=boto3.client('athena',region_name='us-east-1');entry=json.loads((p/'fresh-catalog.json').read_text());queries={
'metadata_catalog':"SELECT source_key,source_record_id,record_kind,raw_completeness_status,ingested_at,json_extract_scalar(labelled_json,'$.payload.data.title') title,json_extract(labelled_json,'$.payload.data.distribution') distributions FROM optima_metadata_engine.source_observations WHERE source_key='cms_payments_catalog' ORDER BY ingested_at DESC LIMIT 3",
'curated_catalog':"SELECT source,provider_id,ingested_at,json_extract_scalar(payload_json,'$.data.title') title,json_extract(payload_json,'$.data.distribution') distributions FROM optima_specialist_inputs.source_observations_windows WHERE source='cms_payments_catalog' AND window_id='"+entry['window_id']+"' LIMIT 3",
'catalog_identities':"SELECT count(*) observations,count(DISTINCT source_record_id) distinct_dataset_ids,count_if(raw_completeness_status='complete') complete FROM optima_metadata_engine.source_observations WHERE source_key='cms_payments_catalog'"}
for name,sql in queries.items():
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];out={'sql':sql,'query_id':q}
 for _ in range(60):
  e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   out.update(state=state,bytes_scanned=e['Statistics'].get('DataScannedInBytes'),reason=e['Status'].get('StateChangeReason'))
   if state=='SUCCEEDED':out['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
   break
  time.sleep(1)
 (p/(name+'.json')).write_text(json.dumps(out,indent=2));print(name,state,q,out.get('reason'),flush=True);assert state=='SUCCEEDED' and len(out['rows'])>1
