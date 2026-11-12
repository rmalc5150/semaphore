import boto3,json,time
from pathlib import Path
a=boto3.client('athena',region_name='us-east-1');out={}
for source,table in [('disclosure_documents','documents_windows'),('disclosure_candidates','event_candidates_windows')]:
 sql=f"SELECT source,dataset,count(*) AS observations,count(DISTINCT record_id) AS distinct_records,count(DISTINCT raw_batch) AS raw_batches,min(ingested_at) AS first_ingested_at,max(ingested_at) AS latest_ingested_at FROM optima_disclosures_pilot.{table} WHERE source='{source}' GROUP BY source,dataset"
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];r={'sql':sql,'query_id':q}
 for _ in range(60):
  execution=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=execution['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   r.update(state=state,bytes_scanned=execution['Statistics'].get('DataScannedInBytes'),reason=execution['Status'].get('StateChangeReason'))
   if state=='SUCCEEDED':r['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
   break
  time.sleep(1)
 else:a.stop_query_execution(QueryExecutionId=q);r['state']='TIMEOUT'
 out[source]=r;Path('repair-notes/2026-11-09-disclosure-review/athena.json').write_text(json.dumps(out,indent=2));print(source,json.dumps(r),flush=True)
