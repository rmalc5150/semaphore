import boto3,json,hashlib
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';files={}
for name in ['news_operations.py','eia_enrichment.py','regulatory_sources.py','constellation/gaps.py','constellation/shared_limits.py','patent_prosecution.py']:
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key='research-data/constellation-backfill/deployments/checkup-20261116-afternoon/'+sha+'/'+name;s.put_object(Bucket=b,Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha':sha}
script='''import os,json,hashlib
from pathlib import Path
import boto3
s=boto3.client('s3');files=FILES;roots=[Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/capture-workers/source'),Path('/opt/constellation/summary-worker'),*Path('/opt/constellation/legacy').glob('*')];changed=[]
for name,meta in files.items():
 raw=s.get_object(Bucket=BUCKET,Key=meta['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==meta['sha'];compile(raw,name,'exec')
 for root in roots:
  target=root/name
  if not target.is_file() or target.read_bytes()==raw:continue
  backup=Path('/opt/constellation/tmp/checkup1116-afternoon-backup')/hashlib.sha256(str(root).encode()).hexdigest()[:12]/name;backup.parent.mkdir(parents=True,exist_ok=True)
  if not backup.exists():backup.write_bytes(target.read_bytes())
  temp=target.with_suffix('.1116pm.tmp');temp.write_bytes(raw);os.chmod(temp,0o644);temp.replace(target);changed.append(str(target))
print(json.dumps({'updated':len(changed),'files':list(files)}))
'''.replace('FILES',repr(files)).replace('BUCKET',repr(b));(p/'deploy.py').write_text(script)
