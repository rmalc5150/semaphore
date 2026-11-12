import json
from pathlib import Path
from collection_storage import StorageSettings
p=Path(__file__).parent;settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();s=__import__('boto3').client('s3',region_name='us-east-1');out=[]
for page in s.get_paginator('list_objects_v2').paginate(Bucket=settings.s3_bucket,Prefix='research-data/constellation-backfill/grants-review/receipts/'):
 for e in page.get('Contents',[]):
  d=json.loads(s.get_object(Bucket=settings.s3_bucket,Key=e['Key'])['Body'].read());out.append(d)
for lane in ('google','odp'):
 v=store.get('constellation-backfill/patent-reviewed/'+lane+'-continuation.json')
 if v:out.append(json.loads(v.body))
(p/'fresh-receipts.json').write_text(json.dumps(out,indent=2));print([(d.get('job',{}).get('source',d.get('lane')),d.get('status',d.get('result',{}).get('status')),d.get('records',d.get('result',{}).get('last_attempt',{}).get('records')),d.get('reason'),d.get('job',{}).get('parameters',{}).get('url'))for d in out])
