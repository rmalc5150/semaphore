import boto3,json,time
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3',region_name='us-east-1');bucket='data-collection-059416028963-us-east-1-an'
try:
 raw=s.get_object(Bucket=bucket,Key='research-data/cms-financial/status.json')['Body'].read();(p/'financial-status-before.json').write_bytes(raw);o=json.loads(raw);print('STATUS',o.get('updated_at'),[(e['title'],e['status'],e.get('error'),e.get('row_count'))for e in o['editions']])
except Exception as e:print(type(e).__name__,str(e)[:100])
a=boto3.client('athena',region_name='us-east-1')
for table in ('cms_financial_editions','cms_open_payments_rows','cms_drug_spending_rows'):
 sql='SELECT '+('source,count(*) editions,sum(row_count) rows'if table=='cms_financial_editions'else'count(*) rows,count(DISTINCT edition_id) editions')+' FROM optima_collected_data.'+table+(' GROUP BY source'if table=='cms_financial_editions'else'')
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];out={'sql':sql,'query_id':q}
 for _ in range(60):
  e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   out.update(state=state,reason=e['Status'].get('StateChangeReason'),bytes_scanned=e['Statistics'].get('DataScannedInBytes'))
   if state=='SUCCEEDED':out['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
   break
  time.sleep(1)
 (p/(table+'-before.json')).write_text(json.dumps(out,indent=2));print(table,json.dumps(out),flush=True)
