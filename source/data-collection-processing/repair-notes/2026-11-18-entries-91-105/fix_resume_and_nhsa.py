from ops import *
import hashlib
refs={}
for name in ['constellation/m7_batch.py','regional_source_review.py']:
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key=BASE+'deployment/'+sha+'/'+name;session.client('s3').put_object(Bucket=B,Key=key,Body=raw,ServerSideEncryption='AES256');refs[name]=(key,sha)
source='china_nhsa_reimbursement_and_procurement'
updates=json.loads((P/'public-source-updates.json').read_text());updates[source]['raw_content_revision']='review-20261118-v2';(P/'public-source-updates.json').write_text(json.dumps(updates,ensure_ascii=False,indent=2)+'\n')
common=r'''import json,hashlib,boto3,os
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');refs=REFS
for root in roots:
 if not root.exists():continue
 for name,(key,sha)in refs.items():
  raw=s.get_object(Bucket=BUCKET,Key=key)['Body'].read();assert hashlib.sha256(raw).hexdigest()==sha;compile(raw,name,'exec');p=root/name;p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.repair-fix');tmp.write_bytes(raw);os.chown(tmp,1000,1000);tmp.replace(p)
 p=root/'config/constellation-public-sources.json'
 if p.exists():
  c=json.loads(p.read_text())
  for row in c['sources']:
   if row['source']=='china_nhsa_reimbursement_and_procurement':row['raw_content_revision']='review-20261118-v2'
  tmp=p.with_name(p.name+'.repair-fix');tmp.write_text(json.dumps(c,indent=2)+'\n');os.chown(tmp,1000,1000);tmp.replace(p)
print('Lifecycle resume fix and bounded NHSA discovery revision installed.')
'''.replace('REFS',repr(refs)).replace('BUCKET',repr(B))
roots="[Path('/opt/constellation/metadata-engine-runtime'),Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/source'),Path('/opt/constellation/legacy/constellation-public-china_nhsa_reimbursement_and_procurement.service')]"
print(remote(M7,'from pathlib import Path\nroots='+roots+'\n'+common)['out'])
code='from pathlib import Path\nroots=[Path.cwd()]\n'+common+r'''
import fcntl,time
from constellation import m7_lifecycle as life,m7_batch as batch
with (life.STATE.parent/'m7-lifecycle.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);assert life.deployment_hold_active();print(json.dumps(batch.remote_control('resume')))
'''
print(remote(T3,code)['out'])
print(remote(T3,r'''import json,os
os.environ['CONSTELLATION_ROLE']='controller';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
from constellation.control import Control
import public_source_capture as pc
c=Control();spec=next(r for r in json.load(open('config/constellation-public-sources.json'))['sources']if r['source']=='china_nhsa_reimbursement_and_procurement');out=pc.run(spec,'daily',limit=2,s3=c.s3);c.s3.put_object(Bucket=BUCKET,Key=BASE+'nhsa-daily-recovery.json',Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256');print(json.dumps(out,default=str))
'''.replace('BUCKET',repr(B)).replace('BASE',repr(BASE)))['out'])
