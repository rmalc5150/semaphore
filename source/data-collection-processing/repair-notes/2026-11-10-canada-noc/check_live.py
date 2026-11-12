import json,time,boto3
from pathlib import Path
from metadata_engine.runtime_db import Database
p=Path(__file__).parent;c=json.load(open('config/metadata-engine.json'));db=Database(c);out={}
with db.tx() as cur:
 for name,sql in {'source':"SELECT source_key,state,contract_version,consecutive_raw_failures,last_reason FROM engine_sources WHERE source_key='canada_noc'",'states':"SELECT state,count(*) n FROM engine_sources GROUP BY state",'jobs':"SELECT state,count(*) n,max(finished_at) latest FROM engine_jobs WHERE source_key='canada_noc' GROUP BY state",'latest_accepted':"SELECT source_key,output_rows,finished_at FROM engine_jobs WHERE state='accepted' ORDER BY finished_at DESC LIMIT 10"}.items():cur.execute(sql);out[name]=cur.fetchall()
(p/'final-status.json').write_text(json.dumps(out,indent=2,default=str));print(json.dumps(out,default=str))
a=boto3.client('athena',region_name='us-east-1');queries={
'metadata_sample':"SELECT source_record_id,ingested_at,contract_version,raw_completeness_status,json_extract_scalar(labelled_json,'$.payload.data.noc_number') application_number,json_extract_scalar(labelled_json,'$.payload.data.noc_crp_product_name') medicine_name,length(labelled_json) payload_characters FROM optima_metadata_engine.source_observations WHERE source_key='canada_noc' ORDER BY ingested_at DESC LIMIT 3",
 'curated_payload':"SELECT source,provider_id,ingested_at,json_extract_scalar(payload_json,'$.data.noc_number') application_number,json_extract_scalar(payload_json,'$.data.noc_crp_product_name') medicine_name,length(payload_json) payload_characters FROM optima_specialist_inputs.source_observations_windows WHERE source='canada_noc' ORDER BY ingested_at DESC LIMIT 3"}

for name,sql in queries.items():
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];r={'query_id':q,'sql':sql}
 for _ in range(60):
  e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   r.update(state=state,reason=e['Status'].get('StateChangeReason'))
   if state=='SUCCEEDED':r['rows']=a.get_query_results(QueryExecutionId=q,MaxResults=4)['ResultSet']['Rows']
   break
  time.sleep(1)
 (p/(name+'.json')).write_text(json.dumps(r,indent=2));print(name,json.dumps(r)[:6000])
