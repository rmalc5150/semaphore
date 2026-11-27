import os,sys,json,subprocess
from pathlib import Path
root=Path('/opt/constellation/metadata-engine-runtime');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
from metadata_engine.runtime_db import Database
config=json.loads((root/'config/metadata-engine.json').read_text());db=Database(config)
with db.tx()as c:
 c.execute('SHOW INDEX FROM engine_jobs');indexes=c.fetchall();print('INDEXES',[(r['Key_name'],r['Column_name'],r['Seq_in_index'])for r in indexes])
 c.execute("SELECT job_id,source_key,state,finished_at,output_rows,report_uri,output_uri FROM engine_jobs FORCE INDEX (publication_ready_order) WHERE state='accepted' ORDER BY finished_at DESC,job_id DESC LIMIT 5");rows=c.fetchall();print('ACCEPTED',json.dumps(rows,default=str))
 c.execute("SELECT job_id,source_key,lease_until FROM engine_jobs FORCE INDEX (work_queue) WHERE state='running' LIMIT 15");print('LEASES',json.dumps(c.fetchall(),default=str))
 c.execute("SELECT source_key,state,last_reason FROM engine_sources WHERE state<>'enabled'");restricted=c.fetchall();print('RESTRICTED',len(restricted));
print('PROC',subprocess.run(['ps','-eo','comm,args'],capture_output=True,text=True).stdout.count('metadata_engine.worker --'))
