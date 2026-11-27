import json,boto3
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';base='research-data/constellation-backfill/repairs/2026-11-16'
for name in ('all-publication-results.json','second-results.json'):
 try:
  d=json.loads(s.get_object(Bucket=b,Key=base+'/'+name)['Body'].read());(p/name).write_text(json.dumps(d,indent=2))
  print(name,{'status':d.get('result',{}).get('status'),'verified':len(d.get('result',{}).get('results',[]))}if'result'in d else{v:sum(r['status']==v for r in d['outcomes'])for v in set(r['status']for r in d['outcomes'])})
 except s.exceptions.NoSuchKey:print(name,'still running')
