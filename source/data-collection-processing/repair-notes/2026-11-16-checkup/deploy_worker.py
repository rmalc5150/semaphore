import os,sys,json,hashlib,subprocess
from pathlib import Path
import boto3
s=boto3.client('s3',region_name='us-east-1');files={'reviewed_source_gaps.py': {'key': 'research-data/constellation-backfill/deployments/checkup-20261116/8a64cc229729039f775f77199ea9fd6c01f01c93b4214ba9c7c953cc625a0a44/reviewed_source_gaps.py', 'sha256': '8a64cc229729039f775f77199ea9fd6c01f01c93b4214ba9c7c953cc625a0a44'}, 'credential_source_apis.py': {'key': 'research-data/constellation-backfill/deployments/checkup-20261116/ba69345468af8d11020bdb015935eae430ebc5274f07cccb02080d15ca684211/credential_source_apis.py', 'sha256': 'ba69345468af8d11020bdb015935eae430ebc5274f07cccb02080d15ca684211'}, 'additional_source_apis.py': {'key': 'research-data/constellation-backfill/deployments/checkup-20261116/07751259ae4d4cc6c0180de6ac196862773d0c6e4c425d99baa2aa671f9bd2d2/additional_source_apis.py', 'sha256': '07751259ae4d4cc6c0180de6ac196862773d0c6e4c425d99baa2aa671f9bd2d2'}, 'specialist_inputs.py': {'key': 'research-data/constellation-backfill/deployments/checkup-20261116/d8dfd4bb31c5ba7172f9d9d9cd2a7cf02b66b588272722a5cb3101fdf28998cf/specialist_inputs.py', 'sha256': 'd8dfd4bb31c5ba7172f9d9d9cd2a7cf02b66b588272722a5cb3101fdf28998cf'}, 'usgs_archive_urls.py': {'key': 'research-data/constellation-backfill/deployments/checkup-20261116/cf595fef33026d514e7390addf8e8ccbdef3ca268bc43017a0746401d441d3c5/usgs_archive_urls.py', 'sha256': 'cf595fef33026d514e7390addf8e8ccbdef3ca268bc43017a0746401d441d3c5'}};out=[]
roots=[Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/capture-workers/source'),*Path('/opt/constellation/legacy').glob('*')]
for root in roots:
 if not(root/'specialist_inputs.py').is_file():continue
 for name,meta in files.items():
  raw=s.get_object(Bucket='data-collection-059416028963-us-east-1-an',Key=meta['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==meta['sha256'];compile(raw,name,'exec');target=root/name
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
