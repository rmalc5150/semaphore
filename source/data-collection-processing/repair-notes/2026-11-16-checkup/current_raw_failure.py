import json,boto3
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';stream='935af362e43726fe97e95f4c6848b591ce8083c6cdf1ec5843bef67f9ae9d53f'
for src in ['hkex-filings','documents']:
 key='research-data/operations/streams/'+stream+'/daily/'+src+'/2026-09-30_2026-10-01.json'
 try:
  d=json.loads(s.get_object(Bucket=b,Key=key)['Body'].read());(p/(src+'-current-failure.json')).write_text(json.dumps(d,indent=2));print(src,d)
 except Exception as e:print(src,type(e).__name__)
