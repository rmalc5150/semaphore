import json,time
from pathlib import Path
from metadata_engine.runtime_db import Database
p=Path(__file__).parent;db=Database(json.load(open('config/metadata-engine.json')));out={'cancelled':[],'indexes':[]}
with db.tx()as c:
 c.execute('SELECT CURRENT_USER() account,USER() connection');account=c.fetchone();c.execute('SHOW FULL PROCESSLIST');rows=c.fetchall();(p/'queue-processes-before.json').write_text(json.dumps({'account':account,'processes':rows},indent=2,default=str))
 runtime_user=account['connection'].split('@')[0]
 for r in rows:
  sql=(r.get('Info')or'').strip();allowed=(sql.startswith('SELECT * FROM engine_jobs WHERE source_key=')and 'ORDER BY priority DESC,created_at,job_id LIMIT 1 FOR UPDATE'in sql)or sql.startswith('SELECT j.* FROM engine_jobs j LEFT JOIN publication_releases r ON ')or sql.startswith('SELECT source_key,contract_version,state,count(*) jobs,sum(output_rows) records FROM engine_jobs WHERE ')
  if r['User']==runtime_user and r['Time']>20 and allowed:
   c.execute('KILL QUERY '+str(int(r['Id'])));out['cancelled'].append({'id':r['Id'],'seconds':r['Time'],'sql':sql})
(p/'database-queue-repair-result.json').write_text(json.dumps(out,indent=2));print(out)
