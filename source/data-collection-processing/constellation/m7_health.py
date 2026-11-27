"""Inspect worker execution where it runs, retaining controller timer evidence."""
import json
import shlex
import time
import boto3
import math

INSTANCE='i-06241bd1c4e91c2fc'
KEY='research-data/constellation-backfill/worker-health/latest.json'
UNITS={'optima-'+name+'.service':'optima-m7-aux-'+name+'.service'for name in (
    'specialist-publication','cms-coverage-publication','crossref-publication-resumed',
    'market-publication','news-publication','cms-catalog-publication',
    'fda-reviewed-publication','grants-reviewed-publication','reviewed-metadata-publication',
    'patents-prosecution-publication','collection-daily')}
UNITS['optima-research-publication.service']='optima-m7-research-publication.service'
UNITS['optima-committed-athena.service']='optima-m7-committed-athena.service'
UNITS['optima-cms-financial-resumed.service']='optima-m7-cms-financial-resumed.service'
UNITS['optima-eodhd-inventory.service']='optima-m7-eodhd-inventory.service'
UNITS['optima-specialist-daily.service']='optima-m7-specialist-daily.service'
from constellation.m7_capture_plan import UNITS as CAPTURE_UNITS
UNITS.update(CAPTURE_UNITS)

def scheduled_sleep(now, instance_state):
    """Recognise bounded, proven batch sleep; never infer health from stale data."""
    if instance_state not in ('stopped', 'stopping'):
        return None
    from constellation.m7_batch import read, policy
    state, settings = read(), policy()
    stopped = state.get('stopped_at')
    if (state.get('phase') != 'sleeping'
            or state.get('drain_proof', {}).get('safe_to_stop') is not True
            or not isinstance(stopped, (int, float)) or not math.isfinite(stopped)):
        return None
    if settings.get('mode') == 'historical_only':
        return {'reason': 'historical_work_threshold_wait', 'stopped_at_epoch': stopped,
                'earliest_wake_at_epoch': stopped + settings['off_hours'] * 3600,
                'historical_wake_hours': settings['historical_wake_hours'],
                'last_history_work': state.get('last_history_work'),
                'instance_state': instance_state}
    deadline = stopped + settings['max_off_hours'] * 3600
    if not stopped <= now < deadline:
        return None
    return {'reason': 'scheduled_batch_sleep', 'stopped_at_epoch': stopped,
            'earliest_wake_at_epoch': stopped + settings['off_hours'] * 3600,
            'wake_deadline_epoch': deadline,
            'queued_requests': len(state.get('requests', {})),
            'instance_state': instance_state}

def refresh(bucket):
    ec2=boto3.client('ec2',region_name='us-east-1')
    state=ec2.describe_instances(InstanceIds=[INSTANCE])['Reservations'][0]['Instances'][0]['State']['Name']
    if state!='running':return state
    code='''import sys,json,time,boto3,subprocess
sys.path.insert(0,'/opt/constellation/auxiliary-publication/source')
from collection_health_exporter import properties,activity,json_reports
doc={'checked_at_epoch':time.time(),'boot_seconds':time.clock_gettime(time.CLOCK_BOOTTIME),'jobs':{}}
for logical,unit in __UNITS__.items():
 try:
  props=properties(unit);status,elapsed=activity(props,True);reports,events,commit=json_reports(unit)
  if not int(props.get('ExecMainStartTimestampMonotonic')or 0) and props.get('ActiveState')=='inactive':
   # Completed remote oneshots can be unloaded: recover times from bounded journal evidence.
   history=subprocess.check_output(['journalctl','-u',unit,'--grep=Starting |Finished |Failed to start','-n','4','--no-pager','-o','json'],text=True)
   for line in history.splitlines():
    row=json.loads(line);message=row.get('MESSAGE','');at=int(row['__REALTIME_TIMESTAMP'])/1e6
    mono=int((doc['boot_seconds']-(doc['checked_at_epoch']-at))*1e6)
    if 'Starting 'in message:props['ExecMainStartTimestampMonotonic']=str(mono)
    elif 'Finished 'in message:props['ExecMainExitTimestampMonotonic']=str(mono)
  doc['jobs'][logical]={'service':props,'activity':status,'elapsed':elapsed,'reports':reports,'events':events,'latest_commit':commit,'worker_unit':unit}
 except Exception as exc:doc['jobs'][logical]={'error':str(exc)[:300]}
boto3.client('s3',region_name='us-east-1').put_object(Bucket=__BUCKET__,Key=__KEY__,Body=json.dumps(doc).encode(),ServerSideEncryption='AES256')
print('Worker health snapshot saved')
'''.replace('__UNITS__',repr(UNITS)).replace('__BUCKET__',repr(bucket)).replace('__KEY__',repr(KEY))
    s=boto3.client('ssm',region_name='us-east-1')
    cmd='/opt/constellation/legacy-venv/bin/python -B -c '+shlex.quote(code)
    identity=s.send_command(InstanceIds=[INSTANCE],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd],'executionTimeout':['60']},TimeoutSeconds=90)['Command']['CommandId']
    end=time.monotonic()+70
    while time.monotonic()<end:
        try:result=s.get_command_invocation(CommandId=identity,InstanceId=INSTANCE)
        except s.exceptions.InvocationDoesNotExist:time.sleep(1);continue
        if result['Status']=='Success':return state
        if result['Status']in ('Failed','TimedOut','Cancelled'):raise RuntimeError('Worker health failed: '+result['StandardErrorContent'][:300])
        time.sleep(1)
    raise RuntimeError('Worker health snapshot timed out')

def view(unit,evidence,now):
    doc,_,_=evidence.read(KEY.removeprefix(evidence.prefix))
    wait = scheduled_sleep(now, getattr(evidence, 'worker_instance_state', None))
    if wait:
        item = dict((doc or {}).get('jobs', {}).get(unit) or {})
        # Keep the previous invocation and source reports as historical evidence.
        # A sleeping instance supplies no current process-health observation.
        item.setdefault('service', {})
        item.setdefault('reports', [])
        item.setdefault('events', [])
        item.setdefault('latest_commit', None)
        item.setdefault('worker_unit', UNITS.get(unit, unit))
        item.update(activity='scheduled_wait', elapsed=0,
                    scheduled_batch_wait={**wait, 'snapshot_checked_at_epoch':
                                          (doc or {}).get('checked_at_epoch')})
        if doc and 'boot_seconds' in doc:
            item['service'] = translated_service(item['service'], doc, now)
        return item
    if not doc or now-doc['checked_at_epoch']>900:raise RuntimeError('m7 execution snapshot missing or older than 15 minutes')
    item=doc['jobs'][unit]
    if item.get('error'):raise RuntimeError(item['error'])
    item=dict(item);props=translated_service(item['service'],doc,now)
    item['service']=props
    if item['activity']in ('running','queued'):item['elapsed']+=max(0,now-doc['checked_at_epoch'])
    return item

def translated_service(service, doc, now):
    props = dict(service)
    # Convert worker monotonic timestamps into this host's clock domain.
    delta=time.clock_gettime(time.CLOCK_BOOTTIME)-doc['boot_seconds']-(now-doc['checked_at_epoch'])
    for field in ('ExecMainStartTimestampMonotonic','ExecMainExitTimestampMonotonic','ActiveEnterTimestampMonotonic'):
        value=int(props.get(field)or 0)
        if value:props[field]=str(int(value+delta*1e6))
    return props
