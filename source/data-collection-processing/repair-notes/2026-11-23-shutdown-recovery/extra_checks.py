import os,sys,json,subprocess
from pathlib import Path
root=Path('/opt/constellation/metadata-engine-runtime');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
from metadata_engine.runtime_db import Database
cfg=json.loads((root/'config/metadata-engine.json').read_text());db=Database(cfg)
with db.tx()as c:
 c.execute("SELECT cursor_json FROM engine_cursors WHERE cursor_key='publication_daily_scan_2bd5e005f9706c9d12532445731f0cb8efc646b0838508f370da9fe15a0bb2dc'");r=c.fetchone();v=json.loads(r['cursor_json']);c.execute('SELECT job_id,source_key,output_rows,output_uri FROM engine_jobs WHERE job_id=%s',(v['job_id'],));print('PUBLISHED_CANDIDATE',json.dumps(c.fetchone()))
print('NOC_UNIT',subprocess.run(['systemctl','cat','optima-canada-noc-daily.service','--no-pager'],capture_output=True,text=True).stdout[-3800:])
print('NOC_LOG',subprocess.run(['journalctl','-u','optima-canada-noc-daily.service','-n','10','-o','cat','--no-pager'],capture_output=True,text=True).stdout[-2500:])
