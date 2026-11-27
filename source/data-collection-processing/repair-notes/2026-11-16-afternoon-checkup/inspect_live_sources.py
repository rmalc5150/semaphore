import boto3,json
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';h=json.load(open(p/'health-before.json'))
for unit in ('optima-news-collection.service','optima-specialist-daily.service'):
 row=h['jobs'][unit];print(unit,'evidence_count',len(row.get('evidence_keys',[])))
 for k in row.get('evidence_keys',[])[-3:]:
  try:
   d=json.loads(s.get_object(Bucket=b,Key='research-data/'+k)['Body'].read());(p/(unit+'-'+k.rsplit('/',1)[-1])).write_text(json.dumps(d,indent=2));print('EVIDENCE',k,'TOP',list(d)[:10]);print(json.dumps(d)[-2200:])
  except Exception as e:print(type(e).__name__)
