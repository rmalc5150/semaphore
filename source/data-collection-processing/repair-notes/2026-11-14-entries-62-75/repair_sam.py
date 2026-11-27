import json,hashlib
from pathlib import Path
from ops import remote,T3,M7,session,B,BASE,P
from metadata_engine.source_policies import build
policy=build(Path.cwd())['sam_gov_opportunities'];files={}
for name in ['metadata_engine/sam_opportunities.py','metadata_engine/evidence.py','metadata_engine/labelling.py','metadata_engine/source_policies.py']:
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key='research-data/constellation-backfill/deployments/entries-62-75-20261114/'+sha+'/'+name;session.client('s3').put_object(Bucket=B,Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
code='''import json,hashlib,os,boto3
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');files=FILES;policy=POLICY
for folder in ROOTS:
 root=Path(folder)
 for name,ref in files.items():
  raw=s.get_object(Bucket=BUCKET,Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];p=root/name;tmp=p.with_suffix('.6275.tmp');tmp.write_bytes(raw);os.chown(tmp,1000,1000);tmp.replace(p)
 p=root/'config/metadata-engine.json';cfg=json.loads(p.read_text());cfg['contracts']['sam_gov_opportunities']=policy;tmp=p.with_suffix('.6275.tmp');tmp.write_text(json.dumps(cfg,indent=2)+'\\n');os.chown(tmp,1000,1000);tmp.replace(p)
'''.replace('FILES',repr(files)).replace('POLICY',repr(policy)).replace('BUCKET',repr(B))
r=remote(M7,code.replace('ROOTS',repr(['/opt/constellation/metadata-engine-runtime','/opt/constellation/auxiliary-publication/source']))+'''import sys,io
os.chdir('/opt/constellation/metadata-engine-runtime');sys.path.insert(0,os.getcwd())
from metadata_engine.sam_opportunities import evidence
before=json.loads(s.get_object(Bucket=BUCKET,Key=BASE+'before.json')['Body'].read());cache={};proof=[]
class Reader:
 def get_object(self,**kw):
  key=kw['Key']
  if key not in cache:
   if len(cache)>=4:cache.clear()
   cache[key]=s.get_object(**kw)['Body'].read(32*1024*1024)
  return {'Body':io.BytesIO(cache[key]),'ContentLength':len(cache[key])}
reader=Reader()
for job in before['sam_gov_opportunities']['failed_jobs']:
 if job['state']!='raw_failed':continue
 try:
  rows=[json.loads(l)for l in s.get_object(Bucket=BUCKET,Key=job['input_key'])['Body'].read().splitlines()if l.strip()]
  for row in rows:evidence(row,reader,BUCKET)
  proof.append({'job_id':job['job_id'],'rows':len(rows),'status':'verified'})
 except Exception as error:proof.append({'job_id':job['job_id'],'status':'failed','reason':str(error)})
s.put_object(Bucket=BUCKET,Key=BASE+'sam-validation.json',Body=json.dumps(proof).encode(),ServerSideEncryption='AES256');print(json.dumps(proof));assert proof and all(p['status']=='verified'for p in proof)
'''.replace('BUCKET',repr(B)).replace('BASE',repr(BASE)));(P/'sam-validation.json').write_text(r['out']);print(r['out'],flush=True)
r=remote(T3,code.replace('ROOTS',repr([str(Path.cwd())]))+'''from metadata_engine.runtime_db import Database,fingerprint
from metadata_engine.controller import register_contract
db=Database(json.load(open('config/metadata-engine.json')));source='sam_gov_opportunities';migrated=[]
with db.tx()as c:
 c.execute('SELECT * FROM engine_sources WHERE source_key=%s FOR UPDATE',(source,));c.fetchone()
 c.execute("SELECT job_id FROM engine_jobs WHERE source_key=%s AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1",(source,));assert not c.fetchone(),'SAM has active work; retry migration after this batch'
 c.execute("SELECT * FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s AND contract_version<>%s AND state IN ('queued','retry','raw_failed')",(source,policy['contract_version']));jobs=c.fetchall();s.put_object(Bucket=BUCKET,Key=BASE+'sam-jobs-before.json',Body=json.dumps(jobs,default=str).encode(),ServerSideEncryption='AES256');register_contract(db,policy,c)
 for job in jobs:
  db.enqueue(source,job['input_key'],job['input_etag'],job['input_format'],500 if job['state']=='raw_failed'else 200,c)
  new=fingerprint([source,job['input_key'],job['input_etag'],job['input_format'],policy['contract_version']]);c.execute("UPDATE engine_jobs SET state='superseded',reason='native_notice_metadata_contract_verified_2.0.3',finished_at=UTC_TIMESTAMP(6) WHERE job_id=%s AND state IN ('queued','retry','raw_failed')",(job['job_id'],));migrated.append({'old':job['job_id'],'new':new,'state':job['state']})
s.put_object(Bucket=BUCKET,Key=BASE+'sam-migration.json',Body=json.dumps(migrated).encode(),ServerSideEncryption='AES256');print(json.dumps({'migrated':len(migrated)}))
'''.replace('BUCKET',repr(B)).replace('BASE',repr(BASE)));print(r['out'])
