import json
from pathlib import Path
from metadata_engine.runtime_db import Database
p=Path(__file__).parent;db=Database(json.load(open('config/metadata-engine.json')));sources=tuple(json.loads((p/'sources.json').read_text()));out={}
with db.tx()as c:
 c.execute("SELECT f.failure_id,f.source_key,f.job_id,f.error_reason FROM pipeline_failures f JOIN engine_jobs j ON j.job_id=f.job_id WHERE f.source_key IN %s AND f.status='open' AND j.state='accepted'",(sources,));out['pipeline_failures']=c.fetchall()
 for r in out['pipeline_failures']:c.execute("UPDATE pipeline_failures SET status='resolved' WHERE failure_id=%s AND status='open'",(r['failure_id'],))
 c.execute("SELECT f.source_key,f.dataset,f.failure_date,f.reason_code,f.latest_job_id FROM source_date_failures f JOIN engine_jobs j ON j.job_id=f.latest_job_id WHERE f.source_key IN %s AND f.status='open' AND j.state='accepted'",(sources,));out['source_date_failures']=c.fetchall()
 for r in out['source_date_failures']:c.execute("UPDATE source_date_failures SET status='resolved' WHERE source_key=%s AND dataset=%s AND failure_date=%s AND reason_code=%s AND latest_job_id=%s",tuple(r[k]for k in ('source_key','dataset','failure_date','reason_code','latest_job_id')))
(p/'resolved-verified-failures.json').write_text(json.dumps(out,indent=2,default=str));print({k:len(v)for k,v in out.items()})
