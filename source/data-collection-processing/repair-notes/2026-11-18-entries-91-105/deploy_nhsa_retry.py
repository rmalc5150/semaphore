from ops import *
import hashlib
raw=Path('public_source_capture.py').read_bytes();sha=hashlib.sha256(raw).hexdigest();key=BASE+'deployment/'+sha+'/public_source_capture.py';session.client('s3').put_object(Bucket=B,Key=key,Body=raw,ServerSideEncryption='AES256')
code=r'''import boto3,json,hashlib,os
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');raw=s.get_object(Bucket=BUCKET,Key=KEY)['Body'].read();assert hashlib.sha256(raw).hexdigest()==SHA;compile(raw,'public_source_capture.py','exec')
for root in roots:
 p=root/'public_source_capture.py';tmp=p.with_name(p.name+'.retry-fix');tmp.write_bytes(raw);os.chown(tmp,1000,1000);tmp.replace(p)
 p=root/'config/constellation-public-sources.json';cfg=json.loads(p.read_text())
 for row in cfg['sources']:
  if row['source']=='china_nhsa_reimbursement_and_procurement':row['http_transient_retries']=1;row['failure_retry_seconds']=900
 tmp=p.with_name(p.name+'.retry-fix');tmp.write_text(json.dumps(cfg,indent=2)+'\n');os.chown(tmp,1000,1000);tmp.replace(p)
print('Scoped NHSA transient HTTP retry installed; provider Retry-After respected.')
'''.replace('BUCKET',repr(B)).replace('KEY',repr(key)).replace('SHA',repr(sha))
for instance,roots in [(M7,"[Path('/opt/constellation/metadata-engine-runtime'),Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/source'),Path('/opt/constellation/legacy/constellation-public-china_nhsa_reimbursement_and_procurement.service')]"),(T3,'[Path.cwd()]')]:print(remote(instance,'from pathlib import Path\nroots='+roots+'\n'+code)['out'])
print(remote(T3,r'''import os,json
os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1';os.environ['CONSTELLATION_ROLE']='controller'
from constellation.control import Control
import public_source_capture as pc
c=Control();spec=next(r for r in json.load(open('config/constellation-public-sources.json'))['sources']if r['source']=='china_nhsa_reimbursement_and_procurement')
key=pc.PREFIX+'/states/daily/'+spec['source']+'/'+spec['raw_content_revision']+'.json';state,token=pc.read_json(c.s3,key)
if state:
 c.s3.put_object(Bucket=BUCKET,Key=BASE+'nhsa-state-before-verified-retry.json',Body=pc.encode(state),ServerSideEncryption='AES256')
 for entry in state['frontier']:
  if entry['url']==spec['seeds'][0]:entry['retry_after']=pc.stamp()
 pc.put(c.s3,key,pc.encode(state),**({'IfMatch':token}if token else{'IfNoneMatch':'*'}))
report=pc.run(spec,'daily',limit=2,s3=c.s3);c.s3.put_object(Bucket=BUCKET,Key=BASE+'nhsa-daily-recovery.json',Body=json.dumps(report,default=str).encode(),ServerSideEncryption='AES256');print(json.dumps(report,default=str))
'''.replace('BUCKET',repr(B)).replace('BASE',repr(BASE)))['out'])
