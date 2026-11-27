import json,time
from pathlib import Path
import boto3
P=Path(__file__).parent;a=boto3.client('athena',region_name='us-east-1');replay=json.loads((P/'replay-publication.json').read_text())
queries={'counts':"SELECT source_key,count(*) observations,count(DISTINCT raw_s3_uri) linked_raw_objects,count_if(raw_completeness_status='complete') complete_raw_observations,min(ingested_at) first_ingested_at,max(ingested_at) latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key IN ('un_comtrade','doe_storage_program','doe_storage_documents','doe_storage_benchmarks','doe_storage_funding') GROUP BY source_key"}
for source in ('un_comtrade','doe_storage_program','doe_storage_documents','doe_storage_benchmarks','doe_storage_funding'):
 ids=[j['job_id']for j in replay['sources'][source]['accepted']];assert ids
 ids_sql=','.join("'"+j+"'"for j in ids)
 queries['sample-'+source]="SELECT source_key,record_kind,source_record_id,raw_completeness_status,ingested_at,json_extract(labelled_json,'$.payload.data') original_record,json_extract(labelled_json,'$.raw_artifacts') raw_artifacts FROM optima_metadata_engine.source_observations WHERE source_key='"+source+"' AND job_id IN ("+ids_sql+") LIMIT 3"
 if source=='doe_storage_documents':queries['doe-kinds']="SELECT record_kind,count(*) observations FROM optima_metadata_engine.source_observations WHERE source_key='doe_storage_documents' AND job_id IN ("+ids_sql+") GROUP BY record_kind"
running={}
for name,sql in queries.items():
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];running[name]={'query_id':q,'sql':sql};print('Started',name,q,flush=True)
deadline=time.monotonic()+100
while time.monotonic()<deadline and any('state'not in r for r in running.values()):
 for name,r in running.items():
  if 'state'in r:continue
  e=a.get_query_execution(QueryExecutionId=r['query_id'])['QueryExecution'];state=e['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   r.update(state=state,reason=e['Status'].get('StateChangeReason'),bytes_scanned=e['Statistics'].get('DataScannedInBytes'))
   if state=='SUCCEEDED':r['rows']=a.get_query_results(QueryExecutionId=r['query_id'])['ResultSet']['Rows']
 time.sleep(1)
for name,r in running.items():
 if 'state'not in r:a.stop_query_execution(QueryExecutionId=r['query_id']);r.update(state='TIMEOUT')
 (P/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n');print(name,r['state'],'rows',len(r.get('rows',[])),r.get('reason'),flush=True)
 assert r['state']=='SUCCEEDED'and len(r['rows'])>1,r
