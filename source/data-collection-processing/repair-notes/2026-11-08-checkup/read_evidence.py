import json,re
from pathlib import Path
import boto3
p=Path(__file__).parent;s=boto3.client('s3',region_name='us-east-1');c=json.load(open('config/collection-monitoring.json'))
for name,key in [('health','health/latest.json'),('state','state/latest.json'),('gaps','health/constellation-gaps.json')]:
 d=json.loads(s.get_object(Bucket=c['bucket'],Key=c['prefix']+'/'+key)['Body'].read());(p/(name+'.json')).write_text(json.dumps(d,indent=2))
 if name=='health':
  print('health',d['checked_at'])
  for k in ['optima-search-capture.service','optima-conference-collection.service']:print(k,json.dumps(d['jobs'].get(k),default=str)[:2500])
 if name=='state':print('notification_errors',d.get('notification_errors'))
text=Path('/home/ec2-user/.codex/attachments/3a018522-9723-4a24-848d-112b61c09e2f/Pasted text.txt').read_text();out={}
for block in text.split('\n\n'):
 if not block.startswith('constellation-history/'):continue
 src=block.split('|')[0].split('/',1)[1]
 if src in out:continue
 urls=re.findall(r's3://[^\s,]+\.json',block)
 if not urls:continue
 b,k=urls[0][5:].split('/',1)
 try:
  d=json.loads(s.get_object(Bucket=b,Key=k)['Body'].read());out[src]=d
  print(src,[(x.get('reason'),x.get('job',{}).get('parameters')) for x in d.get('outcomes',[])][:3])
 except Exception as e:print(src,type(e).__name__)
(p/'receipts.json').write_text(json.dumps(out,indent=2))
