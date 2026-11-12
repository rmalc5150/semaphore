import json
from pathlib import Path
import boto3
from collection_storage import StorageSettings
from committed_data_athena import query
p=Path('repair-notes/2026-10-21-news-patents-disclosures')
s=StorageSettings.load(Path('config/collection-storage.s3.json')).store()
a=boto3.client('athena',region_name='us-east-1');seen=set();out=[];sql=[]
for line in (p/'targeted-publication.log').read_text().splitlines():
 try:e=json.loads(line)
 except ValueError:continue
 owner=e.get('owner')
 if owner not in ('news','disclosures') or 'publication' not in e:continue
 db='optima_news_research' if owner=='news' else 'optima_disclosures_pilot'
 for r in e['publication'].get('results',[]):
  wid=r['window_id']
  if wid in seen:continue
  seen.add(wid)
  receipt=json.loads(s.get('operations/'+owner+'/publication-receipts/'+wid+'.json').body)
  for table,count in receipt['query']['rows']:
   if table not in ['news_articles','documents','event_candidates','disclosures']:continue
   statement="SELECT * FROM "+db+"."+table+"_windows WHERE window_id='"+wid+"'"
   result=query(a,statement+' LIMIT 2')
   metadata=a.get_query_results(QueryExecutionId=result['query_id'],MaxResults=1)['ResultSet']['ResultSetMetadata']['ColumnInfo']
   result['columns']=[x['Name'] for x in metadata]
   (p/('typed-'+wid+'-'+table+'.json')).write_text(json.dumps(result,indent=2))
   out.append({'database':db,'table':table+'_windows','window_id':wid,'count':int(count),'count_query_id':receipt['query']['query_id'],'sample_query_id':result['query_id'],'sample_rows':len(result['rows'])})
   sql.append('-- '+owner+' / '+table+'; verified rows '+count+'\n'+statement+' ORDER BY rand() LIMIT 20;')
(p/'typed-athena-checks.json').write_text(json.dumps(out,indent=2));(p/'typed-checks.sql').write_text('\n\n'.join(sql)+'\n')
print(json.dumps(out,indent=2))
