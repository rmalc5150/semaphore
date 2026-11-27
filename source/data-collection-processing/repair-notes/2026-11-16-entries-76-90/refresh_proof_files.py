import hashlib
from pathlib import Path
from ops import remote,M7,session,B
files={}
for name in ['metadata_engine/raw_catalog_review.py','metadata_engine/public_documents.py','public_source_scope.py']:
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key='research-data/constellation-backfill/deployments/entries-76-90-20261116/'+sha+'/'+name;session.client('s3').put_object(Bucket=B,Key=key,Body=raw,ServerSideEncryption='AES256');files[name]=(key,sha)
print(remote(M7,'''import boto3,hashlib,os
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1')
for name,(key,sha)in FILES.items():
 raw=s.get_object(Bucket=BUCKET,Key=key)['Body'].read();assert hashlib.sha256(raw).hexdigest()==sha;compile(raw,name,'exec')
 for root in ['/opt/constellation/metadata-engine-runtime','/opt/constellation/auxiliary-publication/source']:
  p=Path(root)/name;tmp=p.with_suffix('.review.tmp');tmp.write_bytes(raw);os.chown(tmp,1000,1000);tmp.replace(p)
print('Final original validation fixes installed')
'''.replace('FILES',repr(files)).replace('BUCKET',repr(B)))['out'])
