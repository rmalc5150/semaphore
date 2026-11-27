import boto3,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an'
for name,key in [('health','research-data/monitoring/health/latest.json'),('gaps','research-data/monitoring/health/constellation-gaps.json')]:
 d=json.loads(s.get_object(Bucket=b,Key=key)['Body'].read());(p/(name+'-after.json')).write_text(json.dumps(d,indent=2));print(name,d.get('checked_at'),d.get('backlog_summary'))
 if name=='health':
  for u,row in d.get('jobs',{}).items():
   if row.get('issues'):print(u,[(i['code'],i.get('at'))for i in row['issues']])
def read(day):
 from datetime import date
 d=date.fromisoformat(day);end=date(d.year+(d.month==12),d.month%12+1,1)
 key='research-data/operations/streams/935af362e43726fe97e95f4c6848b591ce8083c6cdf1ec5843bef67f9ae9d53f/historical/fda/'+day+'_'+str(end)+'.json'
 r=json.loads(s.get_object(Bucket=b,Key=key)['Body'].read());return {k:r.get(k)for k in ['start','end','status','reason','error_type','records','manifest','finished_at']}
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(read,json.load(open(p/'fda-replay-dates.json'))))
(p/'fda-outcomes-after.json').write_text(json.dumps(rows,indent=2));print('FDA', {st:sum(r['status']==st for r in rows) for st in set(r['status']for r in rows)})
for wid in ['b494577cf540d8f1ebace452c1b518d682bbc76f7ad309b055a98a5dc3e35910','bb881a4d601ab0f95cc120b90e0f3cd34bf67a65327957e84ca9fc4178446f6d','6cdaf33ee21c535e17195bec838df5e81524381ffe21b4ee764d79ebb98bcf25']:
 try:
  d=json.loads(s.get_object(Bucket=b,Key='research-data/operations/regulatory/publication-receipts/'+wid+'.json')['Body'].read());(p/('fda-receipt-'+wid[:8]+'.json')).write_text(json.dumps(d,indent=2));print('FDA_PUB',wid,d.get('status'))
 except s.exceptions.NoSuchKey:print('FDA_PUB',wid,'not_yet_published')
