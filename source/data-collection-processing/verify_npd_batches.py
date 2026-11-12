import json,re
from pathlib import Path
import boto3
from committed_data_athena import query
P=Path('repair-notes/2026-10-21-news-patents-disclosures');a=boto3.client('athena',region_name='us-east-1');out=json.loads((P/'athena-payload-checks.json').read_text()) if (P/'athena-payload-checks.json').exists() else []
for f in P.glob('*athena*.log'):
 for line in f.read_text(errors='replace').splitlines():
  try:r=json.loads(line)
  except ValueError:continue
  if r.get('stage')!='verified_batch_group':continue
  if any(x['count_query_id']==r['query_id'] for x in out):continue
  q=a.get_query_execution(QueryExecutionId=r['query_id'])['QueryExecution'];assert q['Status']['State']=='SUCCEEDED'
  where=q['Query'].split(' WHERE ',1)[1]
  sample=query(a,'SELECT record_json FROM optima_collected_data.batch_verification_records WHERE '+where+' LIMIT 2')
  name=r['source']+'-'+r['query_id'];(P/(name+'-sample.json')).write_text(json.dumps(sample,indent=2))
  rec=[json.loads(x[0])for x in sample['rows']]
  out.append({'source':r['source'],'records':r['records'],'count_query_id':r['query_id'],'sample_query_id':sample['query_id'],'provider_ids':[x.get('source_record_id')for x in rec],'payload_keys':[list(x.get('payload',{})) for x in rec]})
  (P/'athena-payload-checks.json').write_text(json.dumps(out,indent=2));print(json.dumps(out[-1]),flush=True)
