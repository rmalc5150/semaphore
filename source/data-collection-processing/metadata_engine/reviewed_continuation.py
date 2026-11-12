"""Source-fenced continuation for reviewed grants, procurement and patent queues."""
import argparse,json,time,uuid
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.worker import process
SOURCES=('nih_reporter','nist_robotics_methods','nist_robotics_documents','usa_spending','ted_notices','uspto_assignment_histories','uspto_odp','google_patents_bigquery')

def claim(db,source):
 with db.tx()as c:
  c.execute("SELECT state FROM engine_sources WHERE source_key=%s FOR UPDATE SKIP LOCKED",(source,));row=c.fetchone()
  if not row or row['state']!='enabled':return None
  c.execute("SELECT job_id FROM engine_jobs WHERE source_key=%s AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1",(source,))
  if c.fetchone():return None
  c.execute("SELECT job_id FROM engine_jobs FORCE INDEX (source_ready_order) WHERE source_key=%s AND ((state IN ('queued','retry') AND available_after<=UTC_TIMESTAMP(6)) OR (state='running' AND lease_until<UTC_TIMESTAMP(6))) ORDER BY priority DESC,created_at,job_id LIMIT 1",(source,));candidate=c.fetchone()
  if not candidate:return None
  c.execute('SELECT * FROM engine_jobs WHERE job_id=%s FOR UPDATE',(candidate['job_id'],));job=c.fetchone()
  token=str(uuid.uuid4());c.execute("UPDATE engine_jobs SET state='running',lease_token=%s,lease_until=DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 600 SECOND),attempts=attempts+1 WHERE job_id=%s",(token,job['job_id']));c.execute('UPDATE engine_sources SET updated_at=UTC_TIMESTAMP(6) WHERE source_key=%s',(source,));job['lease_token']=token;return job

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',choices=SOURCES,required=True);a=p.parse_args();config=json.loads((Path(__file__).resolve().parents[1]/'config/metadata-engine.json').read_text());db=Database(config);s3=db.session.client('s3');started=time.monotonic();done=0
 for _ in range(4):
  if time.monotonic()-started>90:break
  job=claim(db,a.source)
  if not job:break
  process(db,s3,config,job);done+=1
 print(json.dumps({'source':a.source,'jobs_processed':done,'elapsed_seconds':round(time.monotonic()-started,2)}),flush=True)
if __name__=='__main__':main()
