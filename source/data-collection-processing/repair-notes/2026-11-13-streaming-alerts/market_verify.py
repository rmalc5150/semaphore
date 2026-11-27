import json,boto3,time,csv
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3',region_name='us-east-1');a=boto3.client('athena',region_name='us-east-1');b='data-collection-059416028963-us-east-1-an';prefix='research-data/operations/market/automation/73d86afe67f4dc0c545538c8917092c07b4bedb8f92bc1cdb4334e66c029f886';out={}
for name in ['aapg-window-ids','aapg-capture-results','aapg-publication']:
 d=json.loads(s.get_object(Bucket=b,Key=prefix+'/repairs/2026-11-13/'+name+'.json')['Body'].read());(p/(name+'.json')).write_text(json.dumps(d,indent=2));out[name]=d
sql="SELECT symbol,count(*) AS price_rows,min(event_date) AS first_price,max(event_date) AS latest_price,count_if(close IS NOT NULL) AS closing_prices,count_if(json_extract_scalar(record_json,'$.payload.provider_symbol')='AAPG.US') AS mapped_rows FROM optima_market_research.market_prices_windows WHERE window_id IN ("+','.join("'"+x+"'"for x in out['aapg-window-ids'])+") GROUP BY symbol";q=a.start_query_execution(QueryString=sql,WorkGroup='optima-market-research')['QueryExecutionId']
for _ in range(45):
 e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
 if state in ('SUCCEEDED','FAILED','CANCELLED'):break
 time.sleep(1)
r={'query_id':q,'sql':sql,'state':state,'reason':e['Status'].get('StateChangeReason'),'rows':a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']if state=='SUCCEEDED'else []};(p/'market-athena-readback.json').write_text(json.dumps(r,indent=2));print(r,flush=True)
counts={};gaps=[]
for lane in ('daily','historical'):
 d=json.loads(s.get_object(Bucket=b,Key=prefix+'/'+lane+'.json')['Body'].read());rows=[]
 for symbol,v in d['symbols'].items():
  if v.get('gaps')or v.get('last_result',{}).get('reason')=='market_empty_price_window_unverified':
   rows.append(symbol)
   for start,g in v.get('gaps',{}).items():gaps.append({'lane':lane,'symbol':symbol,'start':start,'end_exclusive':g['end_exclusive'],'reason':g['reason']})
 counts[lane]=len(rows);out[lane]=d['symbols']['AAPGV.US']
with (p/'remaining-market-windows.csv').open('w')as f:
 w=csv.DictWriter(f,fieldnames=['lane','symbol','start','end_exclusive','reason']);w.writeheader();w.writerows(gaps)
(p/'market-state-after.json').write_text(json.dumps({'unresolved_counts':counts,'aapgv':out},indent=2));print('unresolved',counts,flush=True)
