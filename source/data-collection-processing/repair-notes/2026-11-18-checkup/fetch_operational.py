import boto3,json
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';stream='935af362e43726fe97e95f4c6848b591ce8083c6cdf1ec5843bef67f9ae9d53f'
base='operations/streams/'+stream+'/daily/hkex-filings/'
r=s.list_objects_v2(Bucket=b,Prefix='research-data/'+base)['Contents'];keys=[x for x in r if not x['Key'].rsplit('/',1)[-1].startswith(('progress','reconciliation'))];recent=sorted(keys,key=lambda x:x['LastModified'],reverse=True)[:1]
for item in recent:
 o=json.loads(s.get_object(Bucket=b,Key=item['Key'])['Body'].read());(p/'hkex-latest.json').write_text(json.dumps(o,indent=2));print('HKEX',json.dumps(o)[:1800])
 if o.get('manifest'):
  key=o['manifest'].rsplit('/',1)[0]+'/failure.json'
  try:d=json.loads(s.get_object(Bucket=b,Key='research-data/'+key)['Body'].read());(p/'hkex-failure.json').write_text(json.dumps(d,indent=2));print('HKEX FAILURE',json.dumps(d)[:2000])
  except s.exceptions.NoSuchKey:pass
for lane in ['daily','reconcile']:
 key='research-data/operations/news/automation/4c4eae3c5cc353c83c299b3080b1c54dd90b8dbc541e1929abca34a2a8870b63/finlight/'+lane+'.json';d=json.loads(s.get_object(Bucket=b,Key=key)['Body'].read());(p/('news-'+lane+'.json')).write_text(json.dumps(d,indent=2));print('NEWS',lane,json.dumps(d)[-1500:])
