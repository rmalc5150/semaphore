import boto3,json,time
from pathlib import Path
p=Path(__file__).parent;a=boto3.client('athena',region_name='us-east-1');symbols=sorted({r['symbol']for r in json.load(open(p/'market-gaps.json'))});qmarks=','.join("'"+x.replace("'","''")+"'"for x in symbols);queries={
'market-profiles':("SELECT source_record_id,json_extract_scalar(labelled_json,'$.payload.general.IPODate') ipo_date,json_extract_scalar(labelled_json,'$.payload.general.DelistedDate') delisted_date,json_extract_scalar(labelled_json,'$.payload.general.Name') name,json_extract(labelled_json,'$.payload.source_evidence') evidence FROM (SELECT *,row_number() OVER(PARTITION BY source_record_id ORDER BY ingested_at DESC,labelled_at DESC) r FROM optima_metadata_engine.source_observations WHERE source_key='eodhd' AND dataset='company_profiles' AND source_record_id IN ("+qmarks+")) WHERE r=1",'optima-collected-data'),
'news-recovery':("SELECT source,count(*) records,max(ingested_at) latest_capture FROM optima_news_research.source_observations_windows WHERE window_id='a4f88981d57caae6d8e1c843afc729a424c2324dcfd125178449f10e8b545964' GROUP BY source",'optima-news-research')}
for name,(sql,wg)in queries.items():
 q=a.start_query_execution(QueryString=sql,WorkGroup=wg,ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];out={'query_id':q,'sql':sql}
 for _ in range(65):
  d=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=d['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   out.update(state=state,reason=d['Status'].get('StateChangeReason'),bytes_scanned=d['Statistics'].get('DataScannedInBytes'))
   if state=='SUCCEEDED':out['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
   break
  time.sleep(1)
 (p/(name+'.json')).write_text(json.dumps(out,indent=2));print(name,state,len(out.get('rows',[]))-1,out.get('reason'),flush=True)
