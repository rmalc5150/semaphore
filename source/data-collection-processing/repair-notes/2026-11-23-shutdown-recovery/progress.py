import os,sys,json,subprocess
from pathlib import Path
root=Path('/opt/constellation/metadata-engine-runtime');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
from metadata_engine.runtime_db import Database
cfg=json.loads((root/'config/metadata-engine.json').read_text());db=Database(cfg)
with db.tx()as c:
 c.execute("SELECT cursor_key,cursor_json,updated_at FROM engine_cursors WHERE cursor_key LIKE 'publication%' LIMIT 10");print('PUBLICATION_CURSORS',json.dumps(c.fetchall(),default=str))
 c.execute("SELECT job_id,source_key,finished_at,output_rows,output_uri FROM engine_jobs FORCE INDEX (publication_ready_order) WHERE state='accepted' ORDER BY finished_at DESC,job_id DESC LIMIT 2");print('NEW_ACCEPTED',json.dumps(c.fetchall(),default=str))
print('DAILY_NOC',subprocess.run(['journalctl','-u','optima-canada-noc-daily.service','-n','4','-o','cat','--no-pager'],capture_output=True,text=True).stdout[-1600:])
print('ASSIGNMENT',subprocess.run(['journalctl','-u','optima-m7-capture-assignments-reviewed-historical.service','-n','3','-o','cat','--no-pager'],capture_output=True,text=True).stdout[-1000:])
print('EXECUTORS',subprocess.run(['systemctl','list-units','--state=running','--no-pager','--no-legend','constellation-backfill@*','constellation-legacy-worker@*','constellation-public-worker@*'],capture_output=True,text=True).stdout)
