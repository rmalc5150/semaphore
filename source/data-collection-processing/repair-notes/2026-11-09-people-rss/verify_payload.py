import boto3,json,time
from pathlib import Path
p=Path(__file__).parent;a=boto3.client('athena',region_name='us-east-1');window=json.loads((p/'fresh-publication.json').read_text())['window_ids'][0];sql="SELECT source,provider_id,ingested_at,json_extract_scalar(payload_json,'$.full_text.status') capture_status,length(json_extract_scalar(payload_json,'$.data.content')) article_text_characters,json_extract_scalar(payload_json,'$.full_text.reference.key') article_text_key FROM optima_people_research.source_observations_windows WHERE source='people_rss' AND window_id='"+window+"' LIMIT 1";q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];out={'sql':sql,'query_id':q}
for _ in range(60):
 r=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=r['Status']['State']
 if state in ('SUCCEEDED','FAILED','CANCELLED'):
  out.update(state=state,reason=r['Status'].get('StateChangeReason'))
  if state=='SUCCEEDED':out['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
  break
 time.sleep(1)
else:a.stop_query_execution(QueryExecutionId=q);out['state']='TIMEOUT'
(p/'curated-payload-verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
assert out['state']=='SUCCEEDED' and len(out['rows'])>1
assert out['rows'][1]['Data'][3]['VarCharValue']=='captured' and int(out['rows'][1]['Data'][4]['VarCharValue'])>=250
