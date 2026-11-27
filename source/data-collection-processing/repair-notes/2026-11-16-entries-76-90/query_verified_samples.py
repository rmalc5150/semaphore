from ops import *
import time
r=remote(T3,'''import json
from metadata_engine.runtime_db import Database
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);out={}
for source in SOURCES:
 if source in ('nice_technology_appraisals','decodo_shared_web_retrieval_access_layer'):continue
 ids=[]
 with db.tx()as c:
  c.execute("SELECT job_id FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s AND state='accepted' ORDER BY job_id LIMIT 120",(source,));candidates=c.fetchall()
  for row in candidates:
   c.execute('SELECT j.contract_version,j.output_rows,r.status FROM engine_jobs j LEFT JOIN publication_releases r ON r.release_id=UNHEX(SUBSTRING(j.job_id,1,32)) WHERE j.job_id=%s',(row['job_id'],));v=c.fetchone()
   if v['contract_version']==cfg['contracts'][source]['contract_version']and v['status']=='published':ids.append(row['job_id'])
   if len(ids)>=5:break
 out[source]=ids
print(json.dumps(out))
'''.replace('SOURCES',repr(SOURCES)))
ids=json.loads(r['out']);(P/'verified-sample-job-ids.json').write_text(json.dumps(ids,indent=2));assert all(ids.values()),[(k,v)for k,v in ids.items()if not v]
a=session.client('athena');where=','.join(repr(j)for jobs in ids.values()for j in jobs)
sql="SELECT source_key,dataset,contract_version,count(*) observations,count_if(raw_completeness_status='complete') complete_raw_observations,min(json_extract_scalar(labelled_json,'$.raw_artifacts[1].s3_uri')) provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE job_id IN ("+where+") GROUP BY source_key,dataset,contract_version ORDER BY source_key,dataset"
q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];print(q,flush=True);out={'query_id':q,'sql':sql,'scope':'Up to five published jobs per source; representative verification, not complete source totals.'};deadline=time.monotonic()+120
while time.monotonic()<deadline:
 e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
 if state in ('SUCCEEDED','FAILED','CANCELLED'):break
 time.sleep(1)
else:a.stop_query_execution(QueryExecutionId=q);state='TIMEOUT'
out.update(state=state,status=e['Status'],statistics=e['Statistics'])
if state=='SUCCEEDED':out['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
(P/'verified-sample-sql.json').write_text(json.dumps(out,indent=2,default=str)+'\n');print(state,[[v.get('VarCharValue')for v in row['Data']]for row in out.get('rows',[])],flush=True)
