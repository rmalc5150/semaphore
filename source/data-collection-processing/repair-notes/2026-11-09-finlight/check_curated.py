import boto3,json,time
from pathlib import Path
p=Path(__file__).parent;a=boto3.client('athena',region_name='us-east-1');sql="SELECT source,count(*) row_occurrences,count(DISTINCT record_id) distinct_articles,max(last_observed_at) latest_ingestion FROM optima_news_research.news_articles_windows WHERE source='finlight' GROUP BY source";q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];out={'query_id':q,'sql':sql}
for _ in range(60):
 r=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=r['Status']['State']
 if state in ('SUCCEEDED','FAILED','CANCELLED'):
  out.update(state=state,reason=r['Status'].get('StateChangeReason'),bytes_scanned=r['Statistics'].get('DataScannedInBytes'))
  if state=='SUCCEEDED':out['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
  break
 time.sleep(1)
else:a.stop_query_execution(QueryExecutionId=q);out['state']='TIMEOUT'
(p/'curated-athena-after.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
