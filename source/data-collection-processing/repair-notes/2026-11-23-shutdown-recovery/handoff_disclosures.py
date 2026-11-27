import os,sys,json
from pathlib import Path
root=Path('/opt/constellation/metadata-engine-runtime');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
from metadata_engine.runtime_db import Database
import boto3
cfg=json.loads((root/'config/metadata-engine.json').read_text());db=Database(cfg);s=boto3.client('s3');b=cfg['bucket']
for source in ['documents','press-releases','licensing-agreements','ma-announcements','strategic-transactions']:
 k='research-data/constellation-backfill/repairs/2026-11-23/disclosures-2026-10-14-'+source+'.json';r=json.loads(s.get_object(Bucket=b,Key=k)['Body'].read());m=json.loads(s.get_object(Bucket=b,Key='research-data/'+r['manifest'])['Body'].read());key=m['task']['source']
 with db.tx()as c:
  c.execute('SELECT state FROM engine_sources WHERE source_key=%s',(key,));registered=c.fetchone()
 if not registered or registered['state']!='enabled':print(source,'retained source hold or unregistered',registered);continue
 count=0
 for page in m['pages']:
  for batch in page['batches']:
   path='research-data/'+batch['key'];ref=s.head_object(Bucket=b,Key=path);db.enqueue(key,path,ref['ETag'],'legacy_batch',100);count+=1
 print(source,'metadata_batches',count)
