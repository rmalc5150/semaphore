import boto3,json,time
from pathlib import Path
p=Path(__file__).parent;a=boto3.client('athena',region_name='us-east-1');queries={
'nist-method-pdf':"SELECT source_record_id,ingested_at,json_extract_scalar(labelled_json,'$.payload.data.title') title,length(json_extract_scalar(labelled_json,'$.payload.data.text')) text_chars,json_array_length(json_extract(labelled_json,'$.payload.data.sections')) pages FROM optima_metadata_engine.source_observations WHERE source_key='nist_robotics_methods' AND job_id='a665c068b995b4ac142725aa181f6cb93c392185d3154a8c1ccd9d32880ea808'",
'odp-datasets':"SELECT dataset,count(*) observations FROM optima_metadata_engine.source_observations WHERE source_key='uspto_odp' GROUP BY dataset",
'fresh':"SELECT source_key,dataset,count(*) observations,max(ingested_at) latest_ingested FROM optima_metadata_engine.source_observations WHERE source_key IN ('nih_reporter','nist_robotics_methods','usa_spending','ted_notices','uspto_assignment_histories','uspto_odp','google_patents_bigquery') AND ingested_at>='2026-11-11' GROUP BY source_key,dataset"}
for name,sql in queries.items():
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];r={'sql':sql,'query_id':q}
 for _ in range(60):
  e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   r.update(state=state,reason=e['Status'].get('StateChangeReason'),bytes_scanned=e['Statistics'].get('DataScannedInBytes'))
   if state=='SUCCEEDED':r['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
   break
  time.sleep(1)
 (p/(name+'.json')).write_text(json.dumps(r,indent=2));print(name,state,[[d.get('VarCharValue')for d in x['Data']]for x in r.get('rows',[])],flush=True)
