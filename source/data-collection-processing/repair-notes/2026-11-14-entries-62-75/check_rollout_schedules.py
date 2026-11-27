"""Read live restart needs and scheduled starts for the approved service list."""
import json
from ops import remote,T3,session,B,BASE,P
units=json.loads((P/'preventive-service-role-plan.json').read_text())['units']
code=r'''import json,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
units=__UNITS__
def run(args):return subprocess.run(args,capture_output=True,text=True,check=True).stdout
def props(unit,*keys):return dict(line.split('=',1)for line in run(['systemctl','show',unit,*['--property='+k for k in keys]]).splitlines()if'='in line)
boot=time.time()-time.clock_gettime(time.CLOCK_MONOTONIC);rows=[]
for unit in units:
 service=props(unit,'ActiveState','SubState','Result','ExecMainStatus','ExecMainStartTimestamp','ExecMainStartTimestampMonotonic','ExecMainExitTimestamp','MainPID','InvocationID')
 timer=unit.removesuffix('.service')+'.timer';timer_props=props(timer,'ActiveState','SubState','UnitFileState','NextElapseUSecRealtime','NextElapseUSecMonotonic','LastTriggerUSec','AccuracyUSec','RandomizedDelayUSec')
 dropin=Path('/etc/systemd/system')/(unit+'.d')/'zzzzzzzzzz-service-aws-role.conf';mtime=dropin.stat().st_mtime
 started=float(service.get('ExecMainStartTimestampMonotonic')or 0)/1000000
 rows.append({'unit':unit,'service':service,'timer':timer_props,'credential_config_installed_at':datetime.fromtimestamp(mtime,timezone.utc).isoformat(),'last_start_after_config_change':bool(started and boot+started>=mtime)})
table=run(['systemctl','list-timers','--all','--no-pager',*[u.removesuffix('.service')+'.timer'for u in units]])
r=subprocess.run(['systemctl','list-timers','--all','--output=json','--no-pager',*[u.removesuffix('.service')+'.timer'for u in units]],capture_output=True,text=True)
out={'checked_at':datetime.now(timezone.utc).isoformat(),'services':rows,'schedule_table':table,'timer_json':json.loads(r.stdout)if r.returncode==0 else None,'failed_services':run(['systemctl','list-units','--failed','optima-*','constellation-*','--no-pager','--no-legend'])}
import boto3
key='research-data/constellation-backfill/repairs/entries-62-75-20261114/live-service-schedules.json'
boto3.client('s3',region_name='us-east-1').put_object(Bucket='data-collection-059416028963-us-east-1-an',Key=key,Body=json.dumps(out).encode(),ServerSideEncryption='AES256')
print(json.dumps({'key':key}))
'''.replace('__UNITS__',repr(units))
r=remote(T3,code);raw=session.client('s3').get_object(Bucket=B,Key=json.loads(r['out'])['key'])['Body'].read();(P/'live-service-schedules.json').write_bytes(raw);d=json.loads(raw)
print('Checked',d['checked_at']);print('Started after credential update',sum(v['last_start_after_config_change']for v in d['services']),'of',len(units));print('Current failures:',d['failed_services']or'none');print(d['schedule_table']);print('Timer JSON sample:',(d['timer_json']or[])[:2]);print('Unrefreshed:',[(v['unit'],v['service']['ActiveState'],v['service']['ExecMainStartTimestamp'],v['timer']['NextElapseUSecRealtime'])for v in d['services']if not v['last_start_after_config_change']])
