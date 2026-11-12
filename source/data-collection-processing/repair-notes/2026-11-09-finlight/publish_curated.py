import boto3,json,tempfile
from pathlib import Path
from collection_storage import StorageSettings
from research_contract import load_json
from news_athena import prepare
from window_publication import publish_pending
p=Path(__file__).parent;settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();s=boto3.client('s3',region_name=settings.region);keys=[]
for page in s.get_paginator('list_objects_v2').paginate(Bucket=settings.s3_bucket,Prefix='research-data/operations/news/publication-queue/'):
 keys+=page.get('Contents',[])
selected=None
for item in sorted(keys,key=lambda v:v['LastModified'],reverse=True)[:30]:
 q=json.loads(s.get_object(Bucket=settings.s3_bucket,Key=item['Key'])['Body'].read())
 if q.get('provider')=='finlight'and q.get('start','')>'2026-10-22':selected=q;break
assert selected,'No newer fully completed canonical Finlight day window found'
(p/'curated-window.json').write_text(json.dumps(selected,indent=2));print('Publishing canonical complete query set',selected['start'],len(selected['manifests']),'manifests',flush=True)
with tempfile.TemporaryDirectory(prefix='finlight-publication-')as tmp:
 result=publish_pending(store,settings,'news',load_json(Path('config/news-athena.json')),prepare,Path(tmp),max_windows=1,window_ids=[selected['window_id']])
(p/'curated-publication.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
if result['status']=='failed':raise SystemExit(1)
