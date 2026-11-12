import json,boto3,pymysql
from tracking_mysql_trial import SECRET
from pathlib import Path
c=json.load(open('config/constellation-infrastructure.json'));secret=json.loads(boto3.client('secretsmanager',region_name='us-east-1').get_secret_value(SecretId=SECRET)['SecretString'])
conn=pymysql.connect(host=c['db_host'],user=secret['username'],password=secret['password'],database=c['database'],connect_timeout=10,read_timeout=15,autocommit=True,ssl_ca='config/rds-us-east-1-ca-bundle.pem',ssl_verify_cert=True,ssl_verify_identity=True,cursorclass=pymysql.cursors.DictCursor)
with conn.cursor() as cur:
 cur.execute('SHOW FULL PROCESSLIST');rows=[r for r in cur.fetchall() if r['User'] in ('metadata_engine_worker','constellation_controller') and r['Command']=='Query']
Path('repair-notes/2026-11-08-checkup/database-active-queries.json').write_text(json.dumps(rows,indent=2,default=str));print(json.dumps(rows,default=str))
conn.close()
