import json,time
from pathlib import Path
import boto3
P=Path(__file__).parent;a=boto3.client('athena',region_name='us-east-1')
from ops import SOURCES
sql_sources=','.join("'"+s+"'"for s in SOURCES)
queries={'counts-final':"SELECT source_key,dataset,min(job_id) sample_job_id,min(raw_s3_uri) sample_raw_uri,count(*) observations,count_if(raw_completeness_status='complete') complete_raw_observations,min(ingested_at) first_ingested_at,max(ingested_at) latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key IN ("+sql_sources+") GROUP BY source_key,dataset"}
queries['unido-measurements-final'] = "SELECT json_extract_scalar(labelled_json, '$.payload.data.dataset') provider_dataset,count(*) observations,count_if(json_extract_scalar(labelled_json, '$.payload.data.native_observation.v') IS NOT NULL) numeric_values,count_if(raw_completeness_status='complete') complete_raw_observations FROM optima_metadata_engine.source_observations WHERE source_key='unido_iip_and_indstat' AND dataset='specialist_inputs' GROUP BY 1"
queries['portwatch-dates-final'] = "SELECT json_extract_scalar(labelled_json, '$.event_at.value') activity_date,count(*) observations FROM optima_metadata_engine.source_observations WHERE source_key='imf_portwatch_shipping_activity' AND dataset='specialist_inputs' GROUP BY 1 ORDER BY 1"

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
 (P/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n');print(name,r['state'],[[v.get('VarCharValue')for v in x['Data']]for x in r.get('rows',[])[:30] if name=='counts-final'],flush=True)
