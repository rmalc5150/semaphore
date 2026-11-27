import json,boto3
from pathlib import Path
s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';base='research-data/constellation-backfill/repairs/2026-11-16';p=Path(__file__).parent
jobs=json.loads(s.get_object(Bucket=b,Key=base+'/second-jobs.json')['Body'].read());out=[]
for e in jobs:
 if e['job']['source']=='edinet_filings':continue
 try:
  d=json.loads(s.get_object(Bucket=b,Key=base+'/second-steps/'+e['identity']+'.json')['Body'].read());out.append(d);print({k:d.get(k)for k in ('source','start','status','reason','records','manifest')})
  if d.get('status')=='failed'and d.get('manifest'):
   key='research-data/'+d['manifest'].removesuffix('/final.json')+'/failure.json'
   try:print('DIAGNOSTICS',json.loads(s.get_object(Bucket=b,Key=key)['Body'].read()).get('diagnostics'))
   except s.exceptions.NoSuchKey:pass
 except s.exceptions.NoSuchKey:pass
(p/'second-initial-results.json').write_text(json.dumps(out,indent=2))
