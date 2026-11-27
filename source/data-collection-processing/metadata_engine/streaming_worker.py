"""Resource-bounded streaming workers with disjoint source assignments."""
import argparse,fcntl,json,time,uuid
from contextlib import contextmanager
from pathlib import Path
from metadata_engine.runtime_db import Database,host_excluded_sources,streaming_retry_sql
from metadata_engine.worker import process
from metadata_engine.streaming import session
from metadata_engine.s3_metrics import MeteredS3

DEFAULT_SOURCES=('trade_screening','european_commission_cordis','bis_sdmx_api','hkex_prices','faostat_food_balances','indonesia_esdm_and_geological_agency_mineral_statistics','university_technology_transfer_catalogs_and_reports','personnel_archive','hkex_news')
OPENDART = 'south_korea_fss_opendart'


@contextmanager
def lane_lock(lock_dir, lane):
 # Shared/manual mode remains exclusive against either source-specific lane.
 with (lock_dir/'metadata-streaming-worker.lock').open('a') as common:
  try:
   mode = fcntl.LOCK_EX if lane=='shared' else fcntl.LOCK_SH
   fcntl.flock(common,mode|fcntl.LOCK_NB)
  except BlockingIOError:
   yield False
   return
  if lane=='shared':
   yield True
   return
  with (lock_dir/f'metadata-streaming-{lane}.lock').open('a') as lease:
   try:fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:
    yield False
    return
   yield True


def lane_sources(catalog, lane, source=None):
 if source or lane=='opendart':
  return [source or OPENDART]
 sources = set(DEFAULT_SOURCES)|set(catalog)
 if lane=='general':
  sources.discard(OPENDART)
 return sorted(sources)


def claim(db,source):
 with db.tx()as c:
  c.execute('SELECT source_key,state FROM engine_sources WHERE source_key=%s FOR UPDATE SKIP LOCKED',(source,));r=c.fetchone()
  if not r or r['state']!='enabled':return None
  c.execute("SELECT job_id FROM engine_jobs WHERE source_key=%s AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1 FOR UPDATE",(source,))
  if c.fetchone():return None
  c.execute(f"""SELECT j.* FROM engine_jobs j FORCE INDEX (source_jobs)
            WHERE j.source_key=%s AND {streaming_retry_sql('j.reason')} AND (
              (j.state='retry' AND j.available_after<=UTC_TIMESTAMP(6)) OR
              (j.state='running' AND j.lease_until<UTC_TIMESTAMP(6))
            ) ORDER BY j.created_at,j.job_id LIMIT 1 FOR UPDATE SKIP LOCKED""",(source,))
  job=c.fetchone()
  if not job:return None
  token=str(uuid.uuid4())
  c.execute("UPDATE engine_jobs SET state='running',lease_token=%s,lease_until=DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 20 MINUTE),attempts=attempts+1 WHERE job_id=%s",(token,job['job_id']))
  c.execute('UPDATE engine_sources SET updated_at=UTC_TIMESTAMP(6) WHERE source_key=%s',(source,))
  job['lease_token']=token
  return job

def main():
 p=argparse.ArgumentParser();p.add_argument('--source');p.add_argument('--lane',choices=('shared','general','opendart'),default='shared');p.add_argument('--max-jobs',type=int,default=4);a=p.parse_args()
 if a.source and a.lane!='shared':p.error('--source requires the shared lane')
 root=Path(__file__).resolve().parents[1];lock_dir=Path('/opt/constellation/tmp')if Path('/opt/constellation/tmp').exists()else root/'state';lock_dir.mkdir(exist_ok=True)
 with lane_lock(lock_dir,a.lane) as acquired:
  if not acquired:return
  for parent in (Path('/sys/fs/cgroup')/next(x.split(':',2)[2]for x in Path('/proc/self/cgroup').read_text().splitlines()if x.startswith('0::')).lstrip('/')).parents:
   if parent.name=='constellation-workers.slice':
    maximum=(parent/'memory.max').read_text().strip()
    if maximum!='max'and int((parent/'memory.current').read_text())>int(maximum)-1024**3:
     print(json.dumps({'status':'deferred','reason':'worker_pool_memory_busy'}),flush=True);return
    break
  config=json.loads((root/'config/metadata-engine.json').read_text());db=Database(config);s3=MeteredS3(db.session.client('s3'));start=time.monotonic();done=0
  catalog=db.cursor('streaming_source_catalog')
  sources=[source for source in lane_sources(catalog,a.lane,a.source) if source not in host_excluded_sources()]
  after=db.cursor('streaming_source_rotation').get('after','')
  with session():
   for _ in range(a.max_jobs):
    if time.monotonic()-start>600:break
    ordered=[x for x in sources if x>after]+[x for x in sources if x<=after]
    job=None
    for source in ordered:
     after=source
     try:job=claim(db,source)
     except Exception as e:print(json.dumps({'source':source,'claim_error':type(e).__name__+':'+str(e)[:150]}),flush=True);continue
     if job:break
    if not job:break
    if a.lane!='opendart':db.save_cursor('streaming_source_rotation',{'after':after})
    process(db,s3,config,job);done+=1
  print(json.dumps({'streaming_jobs_processed':done,'lane':a.lane,'elapsed_seconds':round(time.monotonic()-start,2),'s3_requests':s3.counts()}),flush=True)
if __name__=='__main__':main()
