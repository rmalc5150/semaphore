import json,boto3
from pathlib import Path
p=Path(__file__).parent;h=json.load(open(p/'health-after.json'));s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an'
for u in ['optima-patents-prosecution.service','optima-patents-daily.service']:
 for k in h['jobs'][u].get('evidence_keys',[])[-2:]:
  d=json.loads(s.get_object(Bucket=b,Key='research-data/'+k)['Body'].read());(p/(u+'-'+k.rsplit('/',1)[-1])).write_text(json.dumps(d,indent=2));print(u,k,json.dumps(d)[-4500:])
