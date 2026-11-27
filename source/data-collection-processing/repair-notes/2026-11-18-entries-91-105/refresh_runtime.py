from ops import *
import hashlib
refs={}
for name in ['metadata_engine/controller.py','constellation/legacy_dispatch.py']:
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key=BASE+'deployment/'+sha+'/'+name;session.client('s3').put_object(Bucket=B,Key=key,Body=raw,ServerSideEncryption='AES256');refs[name]={'sha256':sha,'key':key}
code=r'''import json,hashlib,boto3,os
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');refs=REFS
roots=ROOTS
for root in roots:
 for name,ref in refs.items():
  raw=s.get_object(Bucket=BUCKET,Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];compile(raw,name,'exec');p=root/name;p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.repair.tmp');tmp.write_bytes(raw);os.chown(tmp,1000,1000);tmp.replace(p)
 p=root/'config/metadata-engine.json'
 if p.exists():
  cfg=json.loads(p.read_text());cfg['build_sha256']=hashlib.sha256(b''.join(v.read_bytes()for v in sorted((root/'metadata_engine').glob('*.py')))).hexdigest();tmp=p.with_name(p.name+'.repair.tmp');tmp.write_text(json.dumps(cfg,indent=2)+'\n');os.chown(tmp,1000,1000);tmp.replace(p)
print(json.dumps({'updated_roots':[str(r)for r in roots],'files':refs}))
'''.replace('REFS',repr(refs)).replace('BUCKET',repr(B))
for instance,roots in [(M7,"[Path('/opt/constellation/metadata-engine-runtime'),Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/source')]"),(T3,'[Path.cwd()]')]:print(remote(instance,code.replace('ROOTS',roots))['out'])
p=P/'deployment-plan.json';plan=json.loads(p.read_text());plan['files'].update({name:ref['sha256']for name,ref in refs.items()});p.write_text(json.dumps(plan,indent=2)+'\n')
