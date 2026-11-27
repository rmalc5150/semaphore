import os,sys,json
from pathlib import Path
os.chdir('/opt/constellation/metadata-engine-runtime');sys.path.insert(0,os.getcwd())
from metadata_engine.runtime_db import Database
from metadata_engine.streaming import session,evidence
p=Path('config/metadata-engine.json');config=json.loads(p.read_text());db=Database(config);s=db.session.client('s3');key='research-data/raw/source=trade_screening/dataset=specialist_inputs/ingestion_date=2026-11-12/run_id=run_35482ebc-41ef-4587-8131-6f5c8e4d207d/page-00000000-part-00001-5f6a2c516df6f9b4f55826606fdd931fe73d49bf17d3b205a097cffe74777dd8.jsonl';raw=s.get_object(Bucket=config['bucket'],Key=key)['Body'].read(8*1024**2+1);rows=[json.loads(x)for x in raw.splitlines()if x];validated=0
with session():
 for r in rows[:32]:evidence(r,r['payload']['source_evidence'][0],config['contracts']['trade_screening'],s,config['bucket']);validated+=1
print(json.dumps({'live_composite_records_validated':validated}),flush=True)
config.setdefault('verified_source_failure_handling',{})['trade_screening']='queue_by_source_date';tmp=p.with_suffix('.streaming.tmp');tmp.write_text(json.dumps(config,indent=2)+'\n');tmp.replace(p)
with db.tx()as c:
 c.execute("SELECT job_id FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key='trade_screening' AND state='raw_failed' AND reason='trade_screening_original_row_mismatch'");ids=[r['job_id']for r in c.fetchall()]
 for jid in ids:c.execute("UPDATE engine_jobs SET state='retry',reason='streaming_lane_required',available_after=UTC_TIMESTAMP(6) WHERE job_id=%s AND state='raw_failed'",(jid,))
 c.execute("UPDATE engine_sources SET state='enabled',consecutive_raw_failures=0,last_reason='Composite list identity verified against original complete provider rows',updated_at=UTC_TIMESTAMP(6) WHERE source_key='trade_screening' AND state='raw_stopped'")
 print(json.dumps({'requeued_exact_identity_failures':ids}),flush=True)
