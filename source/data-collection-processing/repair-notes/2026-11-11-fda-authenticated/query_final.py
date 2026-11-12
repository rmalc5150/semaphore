import boto3,json,time
from pathlib import Path
from metadata_engine.fda_authenticated import SOURCES
p=Path(__file__).parent;a=boto3.client('athena',region_name='us-east-1');queries={};clause=','.join("'"+s+"'"for s in SOURCES)
queries['counts']="SELECT source_key,count(*) observations,count(DISTINCT raw_s3_uri) raw_batches,count_if(raw_completeness_status='complete') complete,min(ingested_at) first_ingested,max(ingested_at) latest_ingested FROM optima_metadata_engine.source_observations WHERE source_key IN ("+clause+") GROUP BY source_key"
for source in SOURCES:queries['sample-'+source]="SELECT source_record_id,ingested_at,raw_completeness_status,json_extract(labelled_json,'$.payload.data') provider_data,json_extract(labelled_json,'$.payload.fda_context') fda_context FROM optima_metadata_engine.source_observations WHERE source_key='"+source+"' ORDER BY ingested_at DESC LIMIT 3"
ids=','.join("'"+e['window_id']+"'"for e in json.loads((p/'fresh-windows.json').read_text()))
queries['native-counts']="SELECT source,count(*) records,min(ingested_at) first_ingested,max(ingested_at) latest_ingested FROM optima_specialist_inputs.source_observations_windows WHERE window_id IN ("+ids+") GROUP BY source"
queries['native-payloads']="SELECT source,provider_id,json_extract(payload_json,'$.data') provider_data FROM optima_specialist_inputs.source_observations_windows WHERE window_id IN ("+ids+") AND provider_id IN ('"+"','".join([json.loads((p/source/'sample-record.json').read_text())['source_record_id']for source in SOURCES])+"') LIMIT 10"
for name,sql in queries.items():
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];out={'sql':sql,'query_id':q}
 for _ in range(70):
  e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   out.update(state=state,bytes_scanned=e['Statistics'].get('DataScannedInBytes'),reason=e['Status'].get('StateChangeReason'))
   if state=='SUCCEEDED':out['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
   break
  time.sleep(1)
 (p/(name+'.json')).write_text(json.dumps(out,indent=2));print(name,state,q,out.get('reason'),flush=True);assert state=='SUCCEEDED'
 if name!='native-payloads':assert len(out.get('rows',[]))>1
