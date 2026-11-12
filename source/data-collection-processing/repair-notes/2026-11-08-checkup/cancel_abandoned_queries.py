import json,boto3,pymysql
from tracking_mysql_trial import SECRET
from pathlib import Path
c=json.load(open('config/constellation-infrastructure.json'));secret=json.loads(boto3.client('secretsmanager',region_name='us-east-1').get_secret_value(SecretId=SECRET)['SecretString'])
conn=pymysql.connect(host=c['db_host'],user=secret['username'],password=secret['password'],database=c['database'],connect_timeout=10,read_timeout=15,autocommit=True,ssl_ca='config/rds-us-east-1-ca-bundle.pem',ssl_verify_cert=True,ssl_verify_identity=True,cursorclass=pymysql.cursors.DictCursor)
with conn.cursor() as cur:
 cur.execute('SHOW FULL PROCESSLIST');rows=[r for r in cur.fetchall() if r['User'] in ('metadata_engine_worker','constellation_controller') and r['Command']=='Query']
Path('repair-notes/2026-11-08-checkup/database-before-cancel.json').write_text(json.dumps(rows,indent=2,default=str));print(json.dumps(rows,default=str))
# Prepared only: execute after explicit approval of database-repair-proposal.md.
cancelled=[]
with conn.cursor() as cur:
 for row in rows:
  query=row.get('Info') or ''
  abandoned=(row['User']=='constellation_controller' and row['Time']>30 and query.startswith('SELECT spec_json,result_json FROM backfill_jobs WHERE source_key='))
  stuck=(row['User']=='metadata_engine_worker' and row['Time']>3600 and query.startswith("SELECT s.source_key FROM engine_sources s WHERE s.state='enabled' AND EXISTS(") and query.endswith('LIMIT 1 FOR UPDATE SKIP LOCKED'))
  if abandoned or stuck:
   cur.execute('CALL mysql.rds_kill_query(%s)',(row['Id'],));cancelled.append(row['Id'])
Path('repair-notes/2026-11-08-checkup/cancelled-queries.json').write_text(json.dumps({'query_ids':cancelled},indent=2))
conn.close()
