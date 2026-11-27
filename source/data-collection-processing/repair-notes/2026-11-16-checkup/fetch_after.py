import json,boto3
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';base='research-data/constellation-backfill/repairs/2026-11-16'
for name in ['publication-results.json','coverage-publication-results.json','second-results.json']:
 try:
  d=json.loads(s.get_object(Bucket=b,Key=base+'/'+name)['Body'].read());(p/name).write_text(json.dumps(d,indent=2));print(name,({v:sum(r['status']==v for r in d['outcomes'])for v in set(r['status']for r in d['outcomes'])}if 'outcomes'in d else d))
 except s.exceptions.NoSuchKey:print(name,'running/not yet available')
for key,name in [('research-data/monitoring/health/latest.json','health-after.json'),('research-data/monitoring/health/constellation-gaps.json','gaps-after.json')]:
 try:
  d=json.loads(s.get_object(Bucket=b,Key=key)['Body'].read());(p/name).write_text(json.dumps(d,indent=2));print(name,d.get('checked_at'),{k:d.get(k)for k in ('flagged_gaps','record_only_gaps')})
  if 'jobs'in d:
   print('ISSUES',[(k,r.get('issues'))for k,r in d['jobs'].items()if r.get('issues')])
 except Exception as e:print(name,type(e).__name__)
