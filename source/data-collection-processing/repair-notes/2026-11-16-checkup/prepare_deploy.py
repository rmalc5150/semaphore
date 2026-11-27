import json,hashlib,ast
from pathlib import Path
import boto3
p=Path(__file__).parent
f=Path('usgs_archive_urls.py');raw=f.read_text();raw=raw.replace('\ndef resolve(url):', "\n# Official USGS 2019 cobalt media page links this replacement PDF (verified 2026-11-16).\nARCHIVES['https://pubs.usgs.gov/periodicals/mcs2019/mcs2019-cobalt.pdf'] = 'https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/atoms/files/mcs-2019-cobal_0.pdf'\n\ndef resolve(url):")
f.write_text(raw)
names=['reviewed_source_gaps.py','credential_source_apis.py','additional_source_apis.py','specialist_inputs.py','usgs_archive_urls.py']
s=boto3.client('s3',region_name='us-east-1');bucket='data-collection-059416028963-us-east-1-an';files={}
for name in names:
 raw=Path(name).read_bytes();compile(raw,name,'exec');sha=hashlib.sha256(raw).hexdigest();key='research-data/constellation-backfill/deployments/checkup-20261116/'+sha+'/'+name
 s.put_object(Bucket=bucket,Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
(p/'deployment-files.json').write_text(json.dumps(files,indent=2))
script='''import os,sys,json,hashlib,subprocess
from pathlib import Path
import boto3
s=boto3.client('s3',region_name='us-east-1');files=FILES;out=[]
roots=[Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/capture-workers/source'),*Path('/opt/constellation/legacy').glob('*')]
for root in roots:
 if not(root/'specialist_inputs.py').is_file():continue
 for name,meta in files.items():
  raw=s.get_object(Bucket=BUCKET,Key=meta['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==meta['sha256'];compile(raw,name,'exec');target=root/name
  old=target.read_bytes()if target.exists()else b''
  if old==raw:continue
  backup=Path('/opt/constellation/tmp/checkup1116-backup')/hashlib.sha256(str(root).encode()).hexdigest()[:12]/name;backup.parent.mkdir(parents=True,exist_ok=True)
  if not backup.exists():backup.write_bytes(old)
  tmp=target.with_suffix('.1116.tmp');tmp.write_bytes(raw);os.chmod(tmp,0o644);tmp.replace(target)
  out.append({'root':str(root),'file':name,'sha256':meta['sha256'],'backup':str(backup)})
 # Check imports in each real execution root before any replay.
 env=dict(os.environ,CONSTELLATION_ROLE='worker',PYTHONPATH=str(root))
 check=subprocess.run([sys.executable,'-c','import specialist_inputs,credential_source_apis,additional_source_apis,reviewed_source_gaps,usgs_archive_urls'],cwd=root,env=env,capture_output=True,text=True)
 if check.returncode:raise RuntimeError(str(root)+':'+check.stderr[-2000:])
print(json.dumps({'updated':out,'import_checks':'passed'}))
'''.replace('FILES',repr(files)).replace('BUCKET',repr(bucket))
(p/'deploy_worker.py').write_text(script)
print('prepared',len(files),'modules')
