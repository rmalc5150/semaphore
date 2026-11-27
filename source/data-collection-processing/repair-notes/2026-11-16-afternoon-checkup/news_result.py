import boto3,json
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';base='research-data/operations/news/automation/4c4eae3c5cc353c83c299b3080b1c54dd90b8dbc541e1929abca34a2a8870b63/finlight/'
for lane in ['daily','reconcile']:
 d=json.loads(s.get_object(Bucket=b,Key=base+lane+'.json')['Body'].read());(p/('news-'+lane+'-after.json')).write_text(json.dumps(d,indent=2));print(lane,json.dumps(d))
