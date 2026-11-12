import json,time,pymysql
from pathlib import Path
from tracking_registry_reset import settings,ca_bundle
p=Path(__file__).parent;session,instance,admin,_=settings();conn=pymysql.connect(host=instance['Endpoint']['Address'],port=instance['Endpoint']['Port'],user=admin['username'],password=admin['password'],database='metadata_engine',ssl_ca=str(ca_bundle()),ssl_verify_cert=True,ssl_verify_identity=True,connect_timeout=10,read_timeout=600,autocommit=True,cursorclass=pymysql.cursors.DictCursor)
with conn.cursor()as c:
 c.execute('SHOW INDEX FROM engine_jobs');existing={r['Key_name']for r in c.fetchall()};parts=[]
 for name,fields in [('source_ready_order','source_key,priority DESC,created_at,job_id,state,available_after,lease_until'),('publication_ready_order','state,finished_at,job_id'),('source_publication_order','source_key,state,finished_at,job_id')]:
  if name not in existing:parts.append('ADD INDEX '+name+' ('+fields+')')
 if parts:
  c.execute('SET SESSION lock_wait_timeout=10');start=time.monotonic();c.execute('ALTER TABLE engine_jobs '+','.join(parts)+', ALGORITHM=INPLACE, LOCK=NONE');print('Index build seconds',time.monotonic()-start,flush=True)
 c.execute('SHOW INDEX FROM engine_jobs');result=c.fetchall();(p/'queue-indexes-after.json').write_text(json.dumps(result,indent=2,default=str));print([(r['Key_name'],r['Column_name'])for r in result])
conn.close()
