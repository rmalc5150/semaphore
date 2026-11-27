import os,sys,json,subprocess
os.chdir('/opt/constellation/metadata-engine-runtime');sys.path.insert(0,os.getcwd())
from metadata_engine.runtime_db import Database
from metadata_engine.streaming_worker import DEFAULT_SOURCES
c=json.load(open('config/metadata-engine.json'));db=Database(c)
with db.tx()as x:
 for source in DEFAULT_SOURCES:
  x.execute("SELECT job_id FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s AND state='retry' AND reason=%s",(source,"ModuleNotFoundError:No module named 'metadata_engine.streaming'"));ids=[r['job_id']for r in x.fetchall()]
  for jid in ids:x.execute("UPDATE engine_jobs SET reason='streaming_lane_required',available_after=UTC_TIMESTAMP(6) WHERE job_id=%s AND state='retry'",(jid,))
  if ids:print(json.dumps({'source':source,'transient_deployment_handoffs':len(ids)}))
 x.execute("UPDATE engine_jobs SET state='retry',reason='streaming_lane_required',available_after=UTC_TIMESTAMP(6) WHERE job_id='7320999dc6740ae6106f5e26b38c80ed36e7c79cf6506d2e7b90dbafdb2f3e12' AND state='accepted' AND output_rows=0");print('Personnel original replay:',x.rowcount)
print(subprocess.run(['systemctl','start','--no-block','optima-metadata-streaming.service'],capture_output=True,text=True).stdout)
