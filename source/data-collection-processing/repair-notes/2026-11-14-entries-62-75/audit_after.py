"""Bounded covering-index audit; preserve individual query failures as findings."""
import json
from ops import remote,T3,session,B,BASE,P,SOURCES
CODE='''import json
from metadata_engine.runtime_db import Database
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');out={}
def query(sql,args):
 with db.tx()as c:
  c.execute('SET SESSION max_execution_time=3000');c.execute(sql,args);return c.fetchall()
for source in SOURCES:
 entry={'audit_warnings':[],'samples':[]}
 tasks=[('source','SELECT * FROM engine_sources WHERE source_key=%s'),
        ('counts','SELECT state,count(*) jobs FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s GROUP BY state')]
 for name,sql in tasks:
  try:entry[name]=query(sql,(source,))
  except Exception as e:entry[name]=[];entry['audit_warnings'].append(name+':'+type(e).__name__+':'+str(e)[:200])
 entry['source']=entry['source'][0]if entry['source']else None
 entry['failed_jobs']=[];entry['native_jobs']=[]
 for state in ['raw_failed','retry','uncommitted','accepted','queued']:
  try:
   ids=query('SELECT job_id FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s AND state=%s ORDER BY job_id LIMIT 4',(source,state))
   for row in ids:
    job=query('SELECT * FROM engine_jobs WHERE job_id=%s',(row['job_id'],))[0]
    entry['failed_jobs'if state in ('raw_failed','retry','uncommitted')else'native_jobs'].append(job)
  except Exception as e:entry['audit_warnings'].append(state+':'+type(e).__name__+':'+str(e)[:200])
 for job in entry['native_jobs'][:2]:
  try:
   r=s.get_object(Bucket=cfg['bucket'],Key=job['input_key']);raw=r['Body'].read(4*1024*1024);r['Body'].close()
   entry['samples'].append({'input_key':job['input_key'],'record':json.loads(raw.splitlines()[0])})
  except Exception as e:entry['samples'].append({'input_key':job['input_key'],'error':type(e).__name__+':'+str(e)[:200]})
 out[source]=entry
 s.put_object(Bucket=cfg['bucket'],Key=BASE+'after.json',Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256')
print(json.dumps({'key':BASE+'after.json','sources':len(out)}))
'''.replace('SOURCES',repr(SOURCES)).replace('BASE',repr(BASE))
r=remote(T3,CODE);key=json.loads(r['out'])['key'];body=session.client('s3').get_object(Bucket=B,Key=key)['Body'].read();(P/'after.json').write_bytes(body)
for source,d in json.loads(body).items():print(source,d['source']['state'],d['counts'],d['audit_warnings'])
