import boto3,json,time
from pathlib import Path
p=Path(__file__).parent;a=boto3.client('athena',region_name='us-east-1');entries=json.load(open(p/'fresh-captures.json'));ids=','.join("'"+e['window_id']+"'"for e in entries);out={}
queries={'metadata_breakdown':"SELECT dataset,record_kind,json_extract_scalar(labelled_json,'$.payload.record_type') payload_record_type,count(*) observations,count_if(raw_completeness_status='complete') complete_raw_observations,max(ingested_at) latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key='nmpa_trials' GROUP BY 1,2,3 ORDER BY 1,2,3",'fresh_window_counts':f"SELECT window_id,count(*) observations,count_if(record_type='clinical_trial') clinical_trials,count_if(record_type='regulatory_event') events FROM optima_regulatory_pilot.research_records_windows WHERE source='nmpa_trials' AND window_id IN ({ids}) GROUP BY 1 ORDER BY 1"}
for name,sql in queries.items():
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];r={'query_id':q,'sql':sql}
 for _ in range(60):
  e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   r.update(state=state,reason=e['Status'].get('StateChangeReason'))
   if state=='SUCCEEDED':r['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
   break
  time.sleep(1)
 out[name]=r;print(name,json.dumps(r),flush=True);assert r.get('state')=='SUCCEEDED'
counts={row['Data'][0]['VarCharValue']:int(row['Data'][1]['VarCharValue'])for row in out['fresh_window_counts']['rows'][1:]};assert counts=={e['window_id']:e['verified_rows']for e in entries},counts
(p/'athena-breakdown.json').write_text(json.dumps(out,indent=2))
