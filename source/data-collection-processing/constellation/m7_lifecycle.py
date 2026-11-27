"""Controller-owned startup and conservative shared-idle shutdown for m7."""
import argparse, subprocess, time, json, fcntl
from pathlib import Path
import boto3

INSTANCE='i-06241bd1c4e91c2fc'
STATE=Path('/home/ec2-user/data-collection-processing/constellation/autostop/m7-shared-idle.txt')

def deployment_hold_active():
 hold=STATE.parent/'m7-deployment-hold.json'
 if not hold.exists():return False
 try:return float(json.loads(hold.read_text())['expires_at'])>time.time()
 except (ValueError,KeyError,TypeError):return True

def online():
 s=boto3.client('ssm',region_name='us-east-1'); end=time.monotonic()+300
 while time.monotonic()<end:
  rows=s.describe_instance_information(Filters=[{'Key':'InstanceIds','Values':[INSTANCE]}])['InstanceInformationList']
  if rows and rows[0]['PingStatus']=='Online':return s
  time.sleep(5)
 raise RuntimeError('m7 SSM agent did not become ready')

def start():
 e=boto3.client('ec2',region_name='us-east-1'); state=e.describe_instances(InstanceIds=[INSTANCE])['Reservations'][0]['Instances'][0]['State']['Name']
 if state=='stopped':
  from constellation.m7_batch import policy
  if policy().get('mode')=='historical_only':raise RuntimeError('Only the historical workload threshold may wake this worker')
  e.start_instances(InstanceIds=[INSTANCE])
 if state in ('stopped','pending'): e.get_waiter('instance_running').wait(InstanceIds=[INSTANCE],WaiterConfig={'Delay':5,'MaxAttempts':36})
 return online()

def metadata_pending():
    """Return whether enabled metadata has work before waking the worker."""
    from metadata_engine.runtime_db import Database
    db=Database(json.loads(Path('/home/ec2-user/data-collection-processing/config/metadata-engine.json').read_text()))
    with db.tx() as c:
        c.execute("SELECT 1 FROM engine_jobs j JOIN engine_sources s ON s.source_key=j.source_key WHERE s.state='enabled' AND j.state IN ('queued','retry','running') LIMIT 1")
        return bool(c.fetchone())

def metadata():
    # Intake belongs on the controller.  Starting m7 before this bounded scan
    # completed made every metadata timer tick wake (or keep awake) a worker
    # even when there was no eligible work.  Dispatch only after intake has
    # succeeded and the durable queue says an enabled job is available.
    result=subprocess.call(['/home/ec2-user/data-collection-processing/.venv-athena/bin/python','-B','-m','metadata_engine.controller','--no-publication'])
    from constellation.m7_batch import policy
    if result==0 and policy().get('mode')!='historical_only' and metadata_pending():
        dispatch('optima-m7-aux-metadata-publication.service')
    return result

def busy():
 if deployment_hold_active():return True
 from constellation.m7_summary_queue import pending
 from constellation.control import Control
 if pending(Control()):return True
 if metadata_pending():return True
 local=subprocess.check_output(['systemctl','list-units','--state=active,activating,deactivating','--no-legend','--plain','optima-metadata*.service','optima-reviewed-metadata*.service','optima-research-publication.service','optima-specialist-publication.service','optima-cms-coverage-publication.service','optima-crossref-publication-resumed.service','optima-market-publication.service','optima-news-publication.service'],text=True).strip()
 if local:return True
 from constellation.control import Control
 historical=Control();enabled=(historical.get('control')or {}).get('enabled')
 with historical.db()as c:
  if enabled:c.execute("SELECT 1 FROM backfill_jobs WHERE status IN ('pending','running','retryable_failed') AND source_key<>'__lease_check__' LIMIT 1")
  else:c.execute("SELECT 1 FROM backfill_jobs WHERE status='running' AND lease_until>=UNIX_TIMESTAMP() AND source_key<>'__lease_check__' LIMIT 1")
  if c.fetchone():return True
 # Long-lived historical executors remain active even when their queue is empty.
 s=online(); cmd="test -z \"$(systemctl list-units --state=active,activating,deactivating --no-legend --plain 'optima-*.service')\""
 r=s.send_command(InstanceIds=[INSTANCE],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=30)['Command']['CommandId']
 for _ in range(20):
  try: x=s.get_command_invocation(CommandId=r,InstanceId=INSTANCE)
  except s.exceptions.InvocationDoesNotExist: time.sleep(1); continue
  if x['Status']=='Success':return False
  if x['Status'] in ('Failed','Cancelled','TimedOut'):return True
  time.sleep(1)
 return True

def autostop():
 from constellation.m7_batch import tick
 print(json.dumps(tick()),flush=True)
 return
 e=boto3.client('ec2',region_name='us-east-1'); state=e.describe_instances(InstanceIds=[INSTANCE])['Reservations'][0]['Instances'][0]['State']['Name']
 if state!='running': STATE.unlink(missing_ok=True); return
 if busy(): STATE.unlink(missing_ok=True); return
 now=time.time(); prior=float(STATE.read_text()) if STATE.exists() else now; STATE.parent.mkdir(parents=True,exist_ok=True); STATE.write_text(str(prior))
 if now-prior>=600 and not busy(): e.stop_instances(InstanceIds=[INSTANCE]); STATE.unlink(missing_ok=True)

def dispatch(unit):
 from constellation.m7_capture_plan import UNITS,PUBLIC_FILE_JOBS
 allowed={'optima-m7-aux-'+n+'.service' for n in ('specialist-publication','cms-coverage-publication','crossref-publication-resumed','market-publication','news-publication')}
 allowed.add('optima-m7-research-publication.service')
 allowed.add('optima-m7-summary-worker.service')
 allowed.update('optima-m7-aux-'+n+'.service'for n in ('cms-catalog-publication','fda-reviewed-publication','grants-reviewed-publication','reviewed-metadata-publication','patents-prosecution-publication','collection-daily','metadata-publication'))
 allowed.add('optima-m7-committed-athena.service')
 allowed.add('optima-m7-cms-financial-resumed.service')
 allowed.add('optima-m7-eodhd-inventory.service')
 allowed.add('optima-m7-specialist-daily.service')
 allowed.update(UNITS.values())
 if unit not in allowed:raise ValueError('invalid publication unit')
 from constellation.m7_batch import METADATA_PROCESSING_UNITS,dispatch_allowed,acknowledged,metadata_retired,policy,enqueue
 if unit in METADATA_PROCESSING_UNITS and metadata_retired():
  print(json.dumps({'status':'retired_metadata_worker','unit':unit}),flush=True)
  return
 from constellation.m7_historical_policy import HISTORICAL_DISPATCH_UNITS
 historical_only=policy().get('mode')=='historical_only'
 if historical_only and unit not in HISTORICAL_DISPATCH_UNITS:
  enqueue(unit)
  print(json.dumps({'status':'held_historical_only','unit':unit}),flush=True)
  return
 public_source=next((source for name,source in PUBLIC_FILE_JOBS.items()if unit=='optima-m7-capture-'+name+'.service'),None)
 if public_source:
  from constellation.control import Control
  from source_pauses import is_paused
  sources=json.loads((Path(__file__).resolve().parents[1]/'config/constellation-public-sources.json').read_text())['sources']
  enabled=next((row.get('enabled',True)for row in sources if row['source']==public_source),False)
  if not Control().daily_allowed()or is_paused(public_source)or not enabled:
   acknowledged(unit)
   print(json.dumps({'status':'daily_capture_paused','source':public_source}),flush=True)
   return
 if not dispatch_allowed(unit,historical_only=historical_only):
  print(json.dumps({'status':'queued_for_batch','unit':unit}),flush=True)
  return
 if historical_only:
  from constellation.control import Control
  if not Control().allowed():return
  ec2=boto3.client('ec2',region_name='us-east-1')
  actual=ec2.describe_instances(InstanceIds=[INSTANCE])['Reservations'][0]['Instances'][0]['State']['Name']
  if actual!='running':return
  s=online()
 else:s=start()
 STATE.unlink(missing_ok=True)
 ident=s.send_command(InstanceIds=[INSTANCE],DocumentName='AWS-RunShellScript',Parameters={'commands':['systemctl start --no-block '+unit]},TimeoutSeconds=60)['Command']['CommandId']
 for _ in range(60):
  try:r=s.get_command_invocation(CommandId=ident,InstanceId=INSTANCE)
  except s.exceptions.InvocationDoesNotExist:time.sleep(1);continue
  if r['Status']=='Success':
   acknowledged(unit)
   return
  if r['Status'] in ('Failed','TimedOut','Cancelled'):raise RuntimeError('dispatch failed: '+ident)
  time.sleep(1)
 raise RuntimeError('dispatch confirmation timed out: '+ident)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=('metadata','autostop','dispatch'));p.add_argument('--unit');a=p.parse_args()
 with (STATE.parent/'m7-lifecycle.lock').open('a')as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX | (fcntl.LOCK_NB if a.mode=='autostop' else 0))
  except BlockingIOError:raise SystemExit(0)
  if a.mode=='dispatch':dispatch(a.unit)
  elif a.mode=='autostop':autostop()
  else:pass
 if a.mode=='metadata':
  result=subprocess.call(['/home/ec2-user/data-collection-processing/.venv-athena/bin/python','-B','-m','metadata_engine.controller','--no-publication'])
  from constellation.m7_batch import policy
  if result==0 and policy().get('mode')!='historical_only' and metadata_pending():
   with (STATE.parent/'m7-lifecycle.lock').open('a')as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    dispatch('optima-m7-aux-metadata-publication.service')
  raise SystemExit(result)
