import json,hashlib,boto3
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';files={}
for name in ['additional_source_apis.py','constellation/gaps.py','reviewed_source_gaps.py','collection_alerts.py','edinet_pipeline.py','disclosure_collection.py','specialist_publication.py']:
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key='research-data/constellation-backfill/deployments/checkup-20261116/'+sha+'/'+name;s.put_object(Bucket=b,Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
script='''import os,json,hashlib,subprocess
from pathlib import Path
import boto3
s=boto3.client('s3');files=FILES;roots=[Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/capture-workers/source'),Path('/opt/constellation/summary-worker/source'),Path('/opt/constellation/summary-worker'),*Path('/opt/constellation/legacy').glob('*')];changed=[]
for name,meta in files.items():
 raw=s.get_object(Bucket=BUCKET,Key=meta['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==meta['sha256'];compile(raw,name,'exec')
 for root in roots:
  target=root/name
  if not target.is_file():continue
  old=target.read_bytes()
  if old==raw:continue
  backup=Path('/opt/constellation/tmp/checkup1116-delta-backup')/hashlib.sha256(str(root).encode()).hexdigest()[:12]/name;backup.parent.mkdir(parents=True,exist_ok=True)
  if not backup.exists():backup.write_bytes(old)
  temp=target.with_suffix('.1116.tmp');temp.write_bytes(raw);os.chmod(temp,0o644);temp.replace(target);changed.append(str(target))
print(json.dumps({'files_updated':len(changed),'summary_service':subprocess.run(['systemctl','cat','optima-m7-summary-worker.service'],capture_output=True,text=True).stdout[-2000:]}))
'''.replace('FILES',repr(files)).replace('BUCKET',repr(b));(p/'delta_worker.py').write_text(script)
# Update controller daily workspaces without altering their stored credentials/configuration.
for root in Path('constellation/daily-workspaces').glob('*'):
 for name in files:
  target=root/name
  if not target.is_file():continue
  backup=p/'daily-backups'/root.name/name;backup.parent.mkdir(parents=True,exist_ok=True)
  if not backup.exists():backup.write_bytes(target.read_bytes())
  temp=target.with_suffix('.1116.tmp');temp.write_bytes(Path(name).read_bytes());temp.replace(target)
print('delta staged')
