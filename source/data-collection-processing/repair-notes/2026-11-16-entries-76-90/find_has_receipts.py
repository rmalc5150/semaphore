from ops import *
s=session.client('s3');prefix='research-data/constellation-backfill/public-capture/athena/';recent=[];pages=0
for page in s.get_paginator('list_objects_v2').paginate(Bucket=B,Prefix=prefix):
 pages+=1;recent.extend(v['Key']for v in page.get('Contents',[])if v['LastModified'].isoformat()>='2026-11-16')
print('pages',pages,'recent',len(recent),flush=True)
from concurrent.futures import ThreadPoolExecutor
import json
def check(key):
 row=json.loads(s.get_object(Bucket=B,Key=key)['Body'].read().splitlines()[0]);return {'receipt_key':key,'record':row}if row.get('source')=='france_has_medicine_assessment_opinions'and row.get('artifact_kind')=='public_document'else None
with ThreadPoolExecutor(max_workers=6)as pool:found=[r for r in pool.map(check,recent)if r]
s.put_object(Bucket=B,Key=BASE+'has-existing-originals.json',Body=json.dumps(found).encode(),ServerSideEncryption='AES256');(P/'has-existing-originals.json').write_text(json.dumps(found,indent=2));print(json.dumps(found))
