import json,time,boto3
from pathlib import Path
p=Path(__file__).parent;a=boto3.client('athena',region_name='us-east-1')
queries={
'metadata_samples':"SELECT source_key,source_record_id,ingested_at,raw_completeness_status,json_extract_scalar(labelled_json,'$.payload.data.title') inventory_title,json_extract_scalar(labelled_json,'$.payload.cms_context.title') document_title,length(json_extract_scalar(labelled_json,'$.payload.cms_context.coverage_criteria_text')) criteria_characters,json_extract_scalar(labelled_json,'$.payload.cms_context.historical_vintage_verified') historical_vintage_verified FROM optima_metadata_engine.source_observations WHERE source_key IN ('cms_coverage','cms_coverage_documents') ORDER BY source_key,ingested_at DESC LIMIT 20",
'metadata_counts':"SELECT source_key,count(*) observations,count(DISTINCT raw_s3_uri) linked_raw_objects,count_if(raw_completeness_status='complete') complete_raw_observations,min(ingested_at) first_ingested_at,max(ingested_at) latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key IN ('cms_coverage','cms_coverage_documents') GROUP BY source_key"}
queries['document_metadata_sample']=queries['metadata_samples'].replace("source_key IN ('cms_coverage','cms_coverage_documents')","source_key='cms_coverage_documents'")
entries=json.loads((p/'daily-windows.json').read_text())
ids=','.join("'"+e['window_id']+"'"for e in entries)
queries['curated_samples']="SELECT source,provider_id,ingested_at,json_extract_scalar(payload_json,'$.data.title') inventory_title,json_extract_scalar(payload_json,'$.data.data[0].title') document_title,length(json_extract_scalar(payload_json,'$.data.data[0].indications_limitations')) raw_criteria_characters,length(payload_json) provider_payload_characters FROM optima_specialist_inputs.source_observations_windows WHERE window_id IN ("+ids+") ORDER BY source,ingested_at DESC LIMIT 20"
queries['document_curated_sample']=queries['curated_samples'].replace("WHERE window_id","WHERE source='cms_coverage_documents' AND window_id")
for name,sql in queries.items():
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];out={'query_id':q,'sql':sql}
 for _ in range(60):
  e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   out.update(state=state,bytes_scanned=e['Statistics'].get('DataScannedInBytes'),reason=e['Status'].get('StateChangeReason'))
   if state=='SUCCEEDED':out['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
   break
  time.sleep(1)
 (p/(name+'.json')).write_text(json.dumps(out,indent=2));print(name,json.dumps(out)[:2600],flush=True)
 assert state=='SUCCEEDED' and len(out['rows'])>1
