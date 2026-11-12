import json,time,boto3,pymysql
from contextlib import contextmanager
from pathlib import Path
from constellation.control import Control
p=Path(__file__).parent;c=Control()
@contextmanager
def admin_cursor():
 from tracking_mysql_trial import SECRET
 session=boto3.Session(region_name='us-east-1')
 instances=session.client('rds').describe_db_instances()['DBInstances']
 matches=[d for d in instances if d.get('MasterUserSecret',{}).get('SecretArn')==SECRET and d['Endpoint']['Address']==c.config['db_host']]
 assert len(matches)==1, 'Admin secret must belong to the configured queue database'
 secret=json.loads(session.client('secretsmanager').get_secret_value(SecretId=SECRET)['SecretString'])
 connection=pymysql.connect(host=c.config['db_host'],user=secret['username'],password=secret['password'],database=c.config['database'],connect_timeout=10,read_timeout=180,write_timeout=30,autocommit=True,cursorclass=pymysql.cursors.DictCursor,ssl_ca='config/rds-us-east-1-ca-bundle.pem',ssl_verify_cert=True,ssl_verify_identity=True)
 try:
  with connection.cursor() as cur:yield cur
 finally:connection.close()
with admin_cursor() as cur:
 cur.execute('SHOW CREATE TABLE backfill_jobs');before=cur.fetchone();(p/'queue-schema-before.json').write_text(json.dumps(before,indent=2,default=str))
 cur.execute('SHOW INDEX FROM backfill_jobs');indexes=cur.fetchall()
 names={r['Key_name'] for r in indexes}
 if 'source_status_updated' not in names:
  cur.execute('SET SESSION lock_wait_timeout=5')
  cur.connection._read_timeout=180
  start=time.monotonic()
  cur.execute('ALTER TABLE backfill_jobs ADD INDEX source_status_updated (source_key,status,updated_at), ALGORITHM=INPLACE, LOCK=NONE')
  print('Index created',round(time.monotonic()-start,2),flush=True)
 cur.execute("EXPLAIN SELECT spec_json,result_json FROM backfill_jobs WHERE source_key=%s AND status='succeeded' ORDER BY updated_at DESC LIMIT 1",('legacy:constellation-specialist-usda_fas_production_supply_and_distribution.service',))
 result=cur.fetchall();(p/'queue-query-plan-after.json').write_text(json.dumps(result,indent=2,default=str));print(json.dumps(result,default=str))
