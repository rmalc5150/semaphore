"""Inspect worker execution where it runs, retaining controller timer evidence."""
import json
import shlex
import time
import boto3

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
    if not doc or now-doc['checked_at_epoch']>900:raise RuntimeError('m7 execution snapshot missing or older than 15 minutes')
    item=doc['jobs'][unit]
    if item.get('error'):raise RuntimeError(item['error'])
    item=dict(item);props=dict(item['service'])
    # Convert worker monotonic timestamps into this host's clock domain.
    delta=time.clock_gettime(time.CLOCK_BOOTTIME)-doc['boot_seconds']-(now-doc['checked_at_epoch'])
    for field in ('ExecMainStartTimestampMonotonic','ExecMainExitTimestampMonotonic','ActiveEnterTimestampMonotonic'):
        value=int(props.get(field)or 0)
        if value:props[field]=str(int(value+delta*1e6))
    item['service']=props
    if item['activity']in ('running','queued'):item['elapsed']+=max(0,now-doc['checked_at_epoch'])
    return item
