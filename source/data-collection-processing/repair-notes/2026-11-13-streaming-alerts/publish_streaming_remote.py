import os,sys,json,subprocess
os.chdir('/opt/constellation/metadata-engine-runtime');sys.path.insert(0,os.getcwd())
from metadata_engine.runtime_db import Database
from metadata_engine.controller import publish
from metadata_engine.streaming_worker import DEFAULT_SOURCES
config=json.load(open('config/metadata-engine.json'));db=Database(config)
with db.tx()as c:
 for source in ('hkex_prices','european_commission_cordis'):
  c.execute("SELECT job_id FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s AND state='raw_failed' AND reason='streaming_archive_no_dataset_or_document'",(source,));ids=[r['job_id']for r in c.fetchall()]
  for jid in ids:c.execute("UPDATE engine_jobs SET state='retry',reason='streaming_lane_required',available_after=UTC_TIMESTAMP(6) WHERE job_id=%s AND state='raw_failed'",(jid,))
  print(json.dumps({'requeued_source':source,'jobs':len(ids)}),flush=True)
for source in DEFAULT_SOURCES:
 try:print(json.dumps({'source':source,'published_jobs':publish(db,source_key=source)}),flush=True)
 except Exception as e:print(json.dumps({'source':source,'publication_error':type(e).__name__+':'+str(e)[:200]}),flush=True)
with db.tx()as c:
 for source in DEFAULT_SOURCES:
  c.execute("SELECT job_id,state,reason,output_rows,finished_at FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s AND finished_at>='2026-11-13 10:00:00' ORDER BY finished_at DESC LIMIT 6",(source,));print(json.dumps({'source':source,'recent_jobs':c.fetchall()},default=str),flush=True)
print(subprocess.run(['systemctl','show','optima-metadata-streaming.service','-p','Result','-p','ActiveState','-p','MemoryPeak'],capture_output=True,text=True).stdout)
print(subprocess.run(['systemctl','show','optima-m7-capture-patents-daily.service','-p','Result','-p','ActiveState'],capture_output=True,text=True).stdout)
print(subprocess.run(['journalctl','-u','optima-m7-capture-patents-daily.service','-n','8','--no-pager'],capture_output=True,text=True).stdout[-5000:])
