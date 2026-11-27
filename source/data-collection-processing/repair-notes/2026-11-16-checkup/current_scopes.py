import json,concurrent.futures
from pathlib import Path
import boto3
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';h=json.load(open(p/'health-before.json'));keys=h['jobs']['optima-collection-daily.service']['evidence_keys']
def one(key):
 try:d=json.loads(s.get_object(Bucket=b,Key='research-data/'+key)['Body'].read());return {'key':key,'data':d}
 except Exception as e:return {'key':key,'error':str(e)[:200]}
with concurrent.futures.ThreadPoolExecutor(max_workers=5)as pool:rows=list(pool.map(one,keys))
(p/'core-daily-current.json').write_text(json.dumps(rows,indent=2))
for r in rows:
 d=r.get('data',{});print(r['key'],{k:d.get(k)for k in ('next_date','last_manifest','pending_dates','last_complete','reason','status')})
