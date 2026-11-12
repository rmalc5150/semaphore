import json,time,boto3
from pathlib import Path
p=Path(__file__).parent;report=json.load(open(p/'fresh-capture.json'));wid=report['window_id'];a=boto3.client('athena',region_name='us-east-1');out={}
queries={'counts':f"SELECT count(*) observations,count(DISTINCT provider_id) unique_medicines,min(ingested_at) first_ingested_at,max(ingested_at) latest_ingested_at FROM optima_specialist_inputs.source_observations_windows WHERE source='ema_medicines' AND window_id='{wid}'",'categories':f"SELECT json_extract_scalar(payload_json,'$.data.category') category,count(*) medicines FROM optima_specialist_inputs.source_observations_windows WHERE source='ema_medicines' AND window_id='{wid}' GROUP BY 1 ORDER BY 1"}
for name,sql in queries.items():
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];r={'query_id':q,'sql':sql}
 for _ in range(60):
  e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   r.update(state=state,reason=e['Status'].get('StateChangeReason'))
   if state=='SUCCEEDED':r['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
   break
  time.sleep(1)
 out[name]=r;assert r.get('state')=='SUCCEEDED',r
rows=out['counts']['rows'][1]['Data'];assert int(rows[0]['VarCharValue'])==int(rows[1]['VarCharValue'])==report['provider_rows']
assert {r['Data'][0]['VarCharValue']:int(r['Data'][1]['VarCharValue'])for r in out['categories']['rows'][1:]}==report['categories']
(p/'snapshot-athena-verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
