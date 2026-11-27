import boto3,json
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an'
try:
 d=json.loads(s.get_object(Bucket=b,Key='research-data/constellation-backfill/repairs/2026-11-16/replay-results.json')['Body'].read());(p/'replay-results.json').write_text(json.dumps(d,indent=2));from collections import Counter;print('REPLAY',dict(Counter(r['status']for r in d['outcomes'])));print('NONCOMPLETE',[(r['source'],r['start'],r['status'],r.get('reason'))for r in d['outcomes']if r['status']not in('complete','accepted_unavailable')]);print('COMPLETE',[(r['source'],r['start'],r.get('records'),r['job_id'])for r in d['outcomes']if r['status']=='complete'])
except s.exceptions.NoSuchKey:print('replay running')
h=json.load(open(p/'health-before.json'))
for key in h['jobs']['optima-news-collection.service']['evidence_keys']:
 d=json.loads(s.get_object(Bucket=b,Key='research-data/'+key)['Body'].read());(p/('news-'+key.rsplit('/',1)[-1])).write_text(json.dumps(d,indent=2));print('NEWS',key,list(d),json.dumps(d)[-1400:])
