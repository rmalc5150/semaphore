import os,sys,json,subprocess
os.chdir('/opt/constellation/metadata-engine-runtime');sys.path.insert(0,os.getcwd())
from metadata_engine.runtime_db import Database
from metadata_engine.streaming_worker import DEFAULT_SOURCES
c=json.load(open('config/metadata-engine.json'));db=Database(c)
with db.tx()as x:
 x.execute('SELECT source_key,state,consecutive_raw_failures,last_reason FROM engine_sources WHERE source_key IN ('+','.join('%s'for _ in DEFAULT_SOURCES)+')',DEFAULT_SOURCES);print(json.dumps({'sources':x.fetchall()}),flush=True)
 x.execute("SELECT job_id,state,reason,output_rows FROM engine_jobs WHERE job_id IN ('cc1d1f02b206d3599cd6e4b7dc054293b9bd5dcb9b0dfc85ff7c79bf1a92ad40','7320999dc6740ae6106f5e26b38c80ed36e7c79cf6506d2e7b90dbafdb2f3e12')");print(json.dumps({'specific_jobs':x.fetchall()}),flush=True)
print(subprocess.run(['systemctl','show','optima-metadata-streaming.timer','optima-metadata-worker.timer','-p','Id','-p','ActiveState','-p','UnitFileState'],capture_output=True,text=True).stdout)
print(subprocess.run(['systemctl','show','optima-metadata-streaming.service','-p','Result','-p','ActiveState','-p','MemoryMax'],capture_output=True,text=True).stdout)
print(subprocess.run(['journalctl','-u','optima-metadata-streaming.service','-n','5','--no-pager'],capture_output=True,text=True).stdout[-5000:])
print('build',c['build_sha256'])
