import json,time,boto3
from pathlib import Path
p=Path(__file__).parent;status=json.loads((p/'financial-status-before.json').read_text());a=boto3.client('athena',region_name='us-east-1')
for name,title,table in [('general','2025 General Payment Data','cms_open_payments_rows'),('research','2025 Research Payment Data','cms_open_payments_rows'),('ownership','2025 Ownership Payment Data','cms_open_payments_rows'),('drug_spending','Medicare Part D Spending by Drug : 2024-01-01','cms_drug_spending_rows')]:
 edition=next(e['edition_id']for e in status['editions']if e['title']==title);sql=f"SELECT * FROM optima_collected_data.{table} WHERE edition_id='{edition}' AND row_number BETWEEN 1 AND 5000 ORDER BY rand() LIMIT 20";q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];out={'sql':sql,'query_id':q}
 for _ in range(60):
  e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   out.update(state=state,bytes_scanned=e['Statistics'].get('DataScannedInBytes'),reason=e['Status'].get('StateChangeReason'))
   if state=='SUCCEEDED':out['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
   break
  time.sleep(1)
 (p/('sample-'+name+'.json')).write_text(json.dumps(out,indent=2));print(name,state,out.get('bytes_scanned'),out.get('reason'),flush=True)
 if state=='SUCCEEDED':
  assert len(out['rows'])>1;columns=[d['VarCharValue']for d in out['rows'][0]['Data']];sample=out['rows'][1]['Data'][columns.index('row_json')]['VarCharValue'];print('FIELDS',list(json.loads(sample))[:15],flush=True)
