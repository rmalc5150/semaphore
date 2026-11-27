from ops import *
import io,tarfile,hashlib
plan=json.loads((P/'deployment-plan.json').read_text());files=list(plan['files']);buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w:gz')as tar:
 for name in files:tar.add(name,arcname=name)
body=buf.getvalue();sha=hashlib.sha256(body).hexdigest();key=BASE+'deployment/'+sha+'.tgz';session.client('s3').put_object(Bucket=B,Key=key,Body=body,ServerSideEncryption='AES256')
common=r'''import json,hashlib,io,tarfile,os,boto3
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');raw=s.get_object(Bucket=BUCKET,Key=KEY)['Body'].read();assert hashlib.sha256(raw).hexdigest()==SHA
files=FILES;payload={}
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz')as archive:
 for name,expected in files.items():
  value=archive.extractfile(name).read();assert hashlib.sha256(value).hexdigest()==expected
  if name.endswith('.py'):compile(value,name,'exec')
  payload[name]=value
out=[]
for root in roots:
 if not root.exists():continue
 label=hashlib.sha256(str(root).encode()).hexdigest()[:16];backup=Path('/opt/constellation/tmp/entries-91-105-backup')/label if str(root).startswith('/opt')else root/'repair-notes/2026-11-18-entries-91-105/deployed-file-backups'
 for name,value in payload.items():
  target=root/name;target.parent.mkdir(parents=True,exist_ok=True);old=backup/name
  if target.exists()and not old.exists():old.parent.mkdir(parents=True,exist_ok=True);old.write_bytes(target.read_bytes())
  tmp=target.with_name(target.name+'.entries-review.tmp');tmp.write_bytes(value);os.chown(tmp,1000,1000);os.chmod(tmp,0o644);tmp.replace(target)
 out.append(str(root))
print(json.dumps({'installed_roots':out,'files':files}))
'''.replace('BUCKET',repr(B)).replace('KEY',repr(key)).replace('SHA',repr(sha)).replace('FILES',repr(plan['files']))
preamble="from pathlib import Path\nroots=[Path('/opt/constellation/metadata-engine-runtime'),Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/source')]\n"
preamble+="roots +=[Path('/opt/constellation/legacy')/('constellation-public-'+s+'.service') for s in "+repr(list(SOURCES))+"]\nroots.append(Path('/opt/constellation/legacy/constellation-specialist-south_korea_fss_opendart.service'))\n"
r=remote(M7,preamble+common);(P/'deployment-code-m7.json').write_text(r['out']);print('M7 code installed and hashes checked.')
r=remote(T3,"from pathlib import Path\nroots=[Path.cwd()]\n"+common);(P/'deployment-code-t3.json').write_text(r['out']);print('Controller code installed; source configurations and controls remain unchanged pending raw proof.')
