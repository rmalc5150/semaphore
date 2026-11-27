import boto3,json
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3',region_name='us-east-1');b='data-collection-059416028963-us-east-1-an'
for name,key in [('health','research-data/monitoring/health/latest.json'),('gaps','research-data/monitoring/health/constellation-gaps.json'),('overview','research-data/monitoring/overview/latest.json')]:
 d=json.loads(s.get_object(Bucket=b,Key=key)['Body'].read());(p/(name+'-before.json')).write_text(json.dumps(d,indent=2));print(name,d.get('checked_at'))
 if name=='health':
  for unit,row in d.get('jobs',{}).items():
   if row.get('issues'):print(unit,row['issues'])
