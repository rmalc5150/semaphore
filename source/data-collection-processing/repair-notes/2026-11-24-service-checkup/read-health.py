import boto3,json
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');p=Path(__file__).parent
for n,k in [('health-after','research-data/monitoring/health/latest.json'),('worker-after','research-data/constellation-backfill/worker-health/latest.json')]:
 d=json.loads(s.get_object(Bucket='data-collection-059416028963-us-east-1-an',Key=k)['Body'].read());(p/(n+'.json')).write_text(json.dumps(d,indent=2));print(n, str(d)[:220])
