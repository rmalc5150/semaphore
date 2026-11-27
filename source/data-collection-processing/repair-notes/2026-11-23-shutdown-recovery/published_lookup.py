import os,sys,json
from pathlib import Path
root=Path('/opt/constellation/metadata-engine-runtime');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
from metadata_engine.runtime_db import Database
cfg=json.loads((root/'config/metadata-engine.json').read_text());db=Database(cfg)
with db.tx()as c:
 c.execute('SHOW INDEX FROM publication_releases');idx=c.fetchall();print('RELEASE_INDEXES',[(r['Key_name'],r['Column_name'])for r in idx])
 c.execute("SELECT cursor_key,cursor_json FROM engine_cursors WHERE cursor_key LIKE 'publication%' LIMIT 100");rows=c.fetchall();ids=[json.loads(r['cursor_json']).get('job_id')for r in rows if json.loads(r['cursor_json']).get('job_id')]
 for identity in ids:
  c.execute("SELECT s3_uri,verified_at,status FROM publication_releases WHERE release_id=UNHEX(SUBSTRING(%s,1,32)) AND release_kind='labelled'",(identity,));r=c.fetchone()
  if r:print('PUBLISHED',identity,json.dumps(r,default=str));break
 else:print('NO_CURSOR_MATCH')
