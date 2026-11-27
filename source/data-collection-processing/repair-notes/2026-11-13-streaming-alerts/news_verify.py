import json,boto3,time
from pathlib import Path
p=Path(__file__).parent;a=boto3.client('athena',region_name='us-east-1');s=boto3.client('s3',region_name='us-east-1');b='data-collection-059416028963-us-east-1-an';w='a4f88981d57caae6d8e1c843afc729a424c2324dcfd125178449f10e8b545964'
receipt=json.loads(s.get_object(Bucket=b,Key='research-data/operations/news/publication-receipts/'+w+'.json')['Body'].read());(p/'news-receipt.json').write_text(json.dumps(receipt,indent=2))
queries={'news-articles':f"SELECT source,count(*) AS records,min(published_at) AS first_published,max(published_at) AS latest_published,count_if(length(title)>0) AS titled,count_if(length(data_json)>2) AS payloads FROM optima_news_research.news_articles_windows WHERE window_id='{w}' GROUP BY source",'news-observations':f"SELECT count(*) AS observations,max(ingested_at) AS latest_ingested FROM optima_news_research.news_observations_windows WHERE window_id='{w}'",'news-payload-sample':f"SELECT source,provider_id,title,source_url,substr(data_json,1,600) payload_sample FROM optima_news_research.news_articles_windows WHERE window_id='{w}' LIMIT 3"}
for name,sql in queries.items():
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-news-research')['QueryExecutionId'];out={'query_id':q,'sql':sql}
 for _ in range(60):
  e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   out.update(state=state,reason=e['Status'].get('StateChangeReason'),bytes_scanned=e['Statistics'].get('DataScannedInBytes'))
   if state=='SUCCEEDED':out['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
   break
  time.sleep(1)
 (p/(name+'.json')).write_text(json.dumps(out,indent=2));print(name,state,out.get('rows',out.get('reason')),flush=True)
