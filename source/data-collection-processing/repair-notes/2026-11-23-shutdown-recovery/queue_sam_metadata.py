import os,sys,json
from pathlib import Path
root=Path('/opt/constellation/metadata-engine-runtime');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
from metadata_engine.runtime_db import Database
import boto3
cfg=json.loads((root/'config/metadata-engine.json').read_text());db=Database(cfg);s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an'
with db.tx()as c:
 c.execute('SELECT source_key,state,last_reason FROM engine_sources WHERE source_key=%s',('sam_gov_opportunities',));source=c.fetchone()
print('SAM_METADATA_SOURCE',json.dumps(source,default=str))
if source and source['state']=='enabled':
 r=json.loads(s.get_object(Bucket=b,Key='research-data/constellation-backfill/repairs/2026-11-23/sam-replay.json')['Body'].read());m=json.loads(s.get_object(Bucket=b,Key='research-data/'+r['manifest'])['Body'].read());count=0
 for page in m['pages']:
  for batch in page['batches']:
   key='research-data/'+batch['key'];head=s.head_object(Bucket=b,Key=key);db.enqueue('sam_gov_opportunities',key,head['ETag'],'legacy_batch',100);count+=1
 print('SAM_BATCHES_ENQUEUED',count)
