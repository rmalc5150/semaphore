import json,boto3,time
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.controller import publish
p=Path(__file__).parent;sources=json.loads((p/'sources.json').read_text());db=Database(json.load(open('config/metadata-engine.json')));out={}
for source in sources:
 counts=[]
 for _ in range(3):
  n=publish(db,source_key=source);counts.append(n)
  if n<5:break
 out[source]=counts;print(source,counts,flush=True)
(p/'publication.json').write_text(json.dumps(out,indent=2))
a=boto3.client('athena',region_name='us-east-1');queries={'counts':"SELECT source_key,count(*) observations,count(DISTINCT raw_s3_uri) raw_batches,count_if(raw_completeness_status='complete') complete,min(ingested_at) first_ingested,max(ingested_at) latest_ingested FROM optima_metadata_engine.source_observations WHERE source_key IN ('"+"','".join(sources)+"') GROUP BY source_key"}
for source in sources:queries['sample-'+source]="SELECT source_record_id,dataset,record_kind,ingested_at,raw_completeness_status,json_extract(labelled_json,'$.payload.data') provider_data,json_extract(labelled_json,'$.quality_flags') flags FROM optima_metadata_engine.source_observations WHERE source_key='"+source+"' LIMIT 3"
for name,sql in queries.items():
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];r={'sql':sql,'query_id':q}
 for _ in range(60):
  e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   r.update(state=state,bytes_scanned=e['Statistics'].get('DataScannedInBytes'),reason=e['Status'].get('StateChangeReason'))
   if state=='SUCCEEDED':r['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
   break
  time.sleep(1)
 (p/(name+'.json')).write_text(json.dumps(r,indent=2));print(name,state,len(r.get('rows',[]))-1,r.get('reason'),flush=True)
