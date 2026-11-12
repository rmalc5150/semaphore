import json,time,boto3
from pathlib import Path
from metadata_engine.runtime_db import Database
p=Path(__file__).parent;db=Database(json.load(open('config/metadata-engine.json')));out={}
with db.tx()as c:
 for name,sql in {'source':"SELECT source_key,state,contract_version,consecutive_raw_failures,last_reason FROM engine_sources WHERE source_key='crossref_proceedings'",'jobs':"SELECT state,input_format,count(*) n FROM engine_jobs WHERE source_key='crossref_proceedings' GROUP BY state,input_format"}.items():c.execute(sql);out[name]=c.fetchall()
(p/'final-status.json').write_text(json.dumps(out,indent=2,default=str));print(json.dumps(out,default=str),flush=True)
a=boto3.client('athena',region_name='us-east-1');entry=json.load(open(p/'fresh-capture.json'));queries={
'metadata_sample':"SELECT source_record_id,ingested_at,raw_completeness_status,json_extract_scalar(labelled_json,'$.payload.data.title[0]') title,json_extract_scalar(labelled_json,'$.payload.data.type') work_type,json_extract_scalar(labelled_json,'$.payload.data.publisher') publisher,length(labelled_json) payload_characters FROM optima_metadata_engine.source_observations WHERE source_key='crossref_proceedings' AND source_record_id='10.51161/v-convesp/78963' ORDER BY ingested_at DESC LIMIT 3",
'curated_payload':"SELECT doi,title,publication_date,ingested_at,json_extract_scalar(data_json,'$.type') work_type,json_extract_scalar(data_json,'$.publisher') publisher,length(data_json) provider_metadata_characters FROM optima_conference_research.conference_observations_windows WHERE window_id='"+entry['window_id']+"' LIMIT 3"}
for name,sql in queries.items():
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];r={'query_id':q,'sql':sql}
 for _ in range(60):
  e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   r.update(state=state,reason=e['Status'].get('StateChangeReason'),bytes_scanned=e['Statistics'].get('DataScannedInBytes'))
   if state=='SUCCEEDED':r['rows']=a.get_query_results(QueryExecutionId=q,MaxResults=4)['ResultSet']['Rows']
   break
  time.sleep(1)
 (p/(name+'.json')).write_text(json.dumps(r,indent=2));print(name,state,r.get('reason'),str(r.get('rows'))[:450],flush=True);assert state=='SUCCEEDED' and len(r.get('rows',[]))>1
