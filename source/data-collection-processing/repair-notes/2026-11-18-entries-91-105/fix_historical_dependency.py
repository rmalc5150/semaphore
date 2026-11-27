from ops import *
import hashlib
name='open_medic_download.py';raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key=BASE+'deployment/'+sha+'/'+name;session.client('s3').put_object(Bucket=B,Key=key,Body=raw,ServerSideEncryption='AES256')
print(remote(M7,r'''import json,hashlib,boto3,os
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');raw=s.get_object(Bucket=BUCKET,Key=KEY)['Body'].read();assert hashlib.sha256(raw).hexdigest()==SHA;compile(raw,'open_medic_download.py','exec');out=[]
for source in SOURCES:
 root=Path('/opt/constellation/legacy')/('constellation-public-'+source+'.service')
 if not root.exists():continue
 p=root/'open_medic_download.py';tmp=p.with_name(p.name+'.dependency-fix');tmp.write_bytes(raw);os.chown(tmp,1000,1000);tmp.replace(p);out.append(str(root))
print(json.dumps({'dependency':'open_medic_download.py','installed_roots':out}))
'''.replace('BUCKET',repr(B)).replace('KEY',repr(key)).replace('SHA',repr(sha)).replace('SOURCES',repr(SOURCES)))['out'])
code=r'''import json,time,boto3
from constellation.control import Control
from constellation.legacy_routes import manifest,specification
from constellation.historical_guard import dispatch_guard
from public_source_capture import read_json,put,encode,PREFIX,stamp
c=Control();specs={r['source']:r for r in json.load(open('config/constellation-public-sources.json'))['sources']};out={}
for source in SOURCES:
 spec=specs.get(source)
 if not spec or not spec.get('enabled',True):continue
 key=PREFIX+'/states/historical/'+source+'/'+spec['raw_content_revision']+'.json';v,etag=read_json(c.s3,key)
 if not v:continue
 failed={url for url,e in v['failures'].items()if e['reason']=='ModuleNotFoundError'}
 if not failed:continue
 c.s3.put_object(Bucket=BUCKET,Key=BASE+'historical-module-failures-before/'+source+'.json',Body=encode(v),ServerSideEncryption='AES256')
 for entry in v['frontier']:
  if entry['url']in failed:entry['retry_after']=stamp()
 put(c.s3,key,encode(v),IfMatch=etag);out[source]={'retried_exact_missing_dependency_urls':len(failed)}
with dispatch_guard(c)as acquired:
 assert acquired and c.allowed()
 for row in manifest()['routes']:
  if not row['execution_enabled']or not any(source in row['unit']for source in out):continue
  with c.db()as q:q.execute("SELECT job_id FROM backfill_jobs WHERE source_key=%s AND status IN ('pending','running','retryable_failed') AND attempts<3 LIMIT 1",('legacy:'+row['unit'],));pending=q.fetchone()
  identity=pending['job_id']if pending else c.register(specification(row,'historical-dependency-recovery-'+str(int(time.time()))))
  with c.db()as q:q.execute("UPDATE backfill_jobs SET updated_at=0,next_attempt_at=0 WHERE job_id=%s AND status IN ('pending','retryable_failed')",(identity,))
  for source in out:
   if source in row['unit']:out[source]['recovery_job_id']=identity
c.s3.put_object(Bucket=BUCKET,Key=BASE+'historical-dependency-recovery.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print(json.dumps(out))
'''.replace('SOURCES',repr(SOURCES)).replace('BUCKET',repr(B)).replace('BASE',repr(BASE))
print(remote(T3,code)['out']);(P/'historical-dependency-recovery.json').write_bytes(session.client('s3').get_object(Bucket=B,Key=BASE+'historical-dependency-recovery.json')['Body'].read())
