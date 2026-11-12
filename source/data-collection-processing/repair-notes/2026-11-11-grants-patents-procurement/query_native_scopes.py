import json,time,boto3
from pathlib import Path
p=Path(__file__).parent;a=boto3.client('athena',region_name='us-east-1');ids=['3ebc778770384cb2a45a77bdce0a54064109afb3c9b71507eb70bcd70bc3e108','4d811c08ba1f58c321b8ca61dd2fdb8abd8ef3de16587346e7e850c0e6baef05','fa4ff2339d7c3005fc2f247590af4f8b68db4e3a3c007ec77abe4758874820ed','bb020b4083d734bfd03a00cf8d404b5125d715f4894fea28bdc64f0db2cb8e68','25f8728cfb2e2be72f52d7992eccf14d942d752c2c7e8b668ca88c33d08d01e1'];sql="SELECT source,count(*) records FROM optima_specialist_inputs.source_observations_windows WHERE window_id IN ('"+"','".join(ids)+"') GROUP BY source";q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data')['QueryExecutionId'];out={'query_id':q,'sql':sql}
for _ in range(60):
 e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
 if state in ('SUCCEEDED','FAILED','CANCELLED'):
  out.update(state=state,reason=e['Status'].get('StateChangeReason'))
  if state=='SUCCEEDED':out['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
  break
 time.sleep(1)
(p/'native-scopes.json').write_text(json.dumps(out,indent=2));print(out)
