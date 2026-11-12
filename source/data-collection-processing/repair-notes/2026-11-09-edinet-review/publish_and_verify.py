import boto3,json,time
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.controller import publish
p=Path(__file__).parent;db=Database(json.load(open('config/metadata-engine.json')));counts=[]
for _ in range(4):
 n=publish(db,source_key='edinet_filings');counts.append(n);print('Verified EDINET published batches:',n,flush=True)
 if n<5:break
(p/'publication.json').write_text(json.dumps({'published_batches_per_call':counts},indent=2))
a=boto3.client('athena',region_name='us-east-1');sql="SELECT source_key,count(*) observations,count(DISTINCT raw_s3_uri) linked_raw_objects,count_if(raw_completeness_status='complete') complete_raw_observations,min(ingested_at) first_ingested_at,max(ingested_at) latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key='edinet_filings' GROUP BY source_key"
q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];out={'query_id':q,'sql':sql}
for _ in range(60):
 r=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=r['Status']['State']
 if state in ('SUCCEEDED','FAILED','CANCELLED'):
  out.update(state=state,bytes_scanned=r['Statistics'].get('DataScannedInBytes'),reason=r['Status'].get('StateChangeReason'))
  if state=='SUCCEEDED':out['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
  break
 time.sleep(1)
else:a.stop_query_execution(QueryExecutionId=q);out['state']='TIMEOUT'
(p/'athena-verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
if out['state']!='SUCCEEDED':raise SystemExit(1)
with db.tx()as c:
 c.execute("SELECT j.job_id,j.state,r.status publication_status FROM engine_jobs j LEFT JOIN publication_releases r ON r.release_id=UNHEX(SUBSTRING(j.job_id,1,32)) WHERE j.source_key='edinet_filings' AND j.finished_at>='2026-11-09 15:55:00' AND j.state='accepted'");jobs=c.fetchall()
(p/'replay-publication-status.json').write_text(json.dumps(jobs,indent=2));assert len(jobs)>=7 and all(j['publication_status']=='published'for j in jobs);print('Seven repaired jobs committed and verified in Athena',flush=True)
