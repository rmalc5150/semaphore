"""Apply only the exact service credential plan explicitly approved by the owner."""
import json,hashlib
from datetime import datetime,timezone
from ops import remote,T3,session,B,BASE,P
plan_path=P/'preventive-service-role-plan.json';raw=plan_path.read_bytes();plan=json.loads(raw)
assert len(plan['units'])==44 and len(set(plan['units']))==44 and not plan['restarts']
code=r'''import json,hashlib,os,re,shlex,subprocess,tempfile
from pathlib import Path
from datetime import datetime,timezone
from source_pauses import unit_pause
plan=__APPROVED_PLAN__
expected={'AWS_CONFIG_FILE':'/dev/null','AWS_SHARED_CREDENTIALS_FILE':'/dev/null','AWS_DEFAULT_REGION':'us-east-1','AWS_REGION':'us-east-1','AWS_EC2_METADATA_DISABLED':'false'}
custom=('AWS_CONFIG_FILE','AWS_SHARED_CREDENTIALS_FILE','AWS_PROFILE','AWS_DEFAULT_PROFILE','AWS_ROLE_ARN','AWS_WEB_IDENTITY_TOKEN_FILE','AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_SESSION_TOKEN')
def show(unit,*keys):
 r=subprocess.run(['systemctl','show',unit,*['--property='+k for k in keys]],capture_output=True,text=True,check=True)
 return dict(line.split('=',1)for line in r.stdout.splitlines()if'='in line)
def environment(props):
 return dict(item.split('=',1)for item in shlex.split(props.get('Environment',''))if'='in item)
out={'started_at':datetime.now(timezone.utc).isoformat(),'host':'t3','approved_units':plan['units'],'approved_plan_sha256':__PLAN_SHA__,'owner_approval':'Explicit user approval of preventive 44-service rollout in this conversation','installed':[],'already_installed':[],'skipped':[],'verification':[],'service_restarts_requested':[],'commands':['systemctl daemon-reload']}
ready=[]
assert re.fullmatch(r'[a-z0-9-]+\.conf',plan['dropin_name']) and len(plan['units'])==44
for unit in plan['units']:
 assert re.fullmatch(r'(optima|constellation)-[a-z0-9-]+\.service',unit)
 props=show(unit,'WorkingDirectory','Environment','LoadState','ActiveState','SubState','InvocationID')
 timer=show(unit.removesuffix('.service')+'.timer','ActiveState','UnitFileState')
 folder=Path('/etc/systemd/system')/(unit+'.d');target=folder/plan['dropin_name'];reason=None
 if unit_pause(unit):reason='currently_paused_or_retired'
 elif props.get('LoadState')!='loaded' or not props.get('WorkingDirectory','').startswith('/home/ec2-user/data-collection-processing'):reason='workspace_or_load_state_changed'
 elif timer.get('ActiveState')!='active' or timer.get('UnitFileState')!='enabled':reason='timer_no_longer_enabled_and_active'
 elif folder.is_symlink()or target.is_symlink():reason='unexpected_symlink_preserved'
 elif target.exists():
  if target.read_text()==plan['dropin_content']:out['already_installed'].append(unit);continue
  reason='existing_dropin_differs_preserved'
 elif any(key in environment(props)for key in custom):reason='explicit_credential_settings_added_since_plan_preserved'
 if reason:out['skipped'].append({'unit':unit,'reason':reason});continue
 ready.append((unit,folder,target,props))
for unit,folder,target,props in ready:
 if unit_pause(unit):out['skipped'].append({'unit':unit,'reason':'pause_added_during_preflight'});continue
 folder.mkdir(exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix='.approved-role-',dir=folder)
 try:
  with os.fdopen(fd,'w')as f:f.write(plan['dropin_content']);f.flush();os.fsync(f.fileno())
  os.chmod(tmp,0o644)
  # Link creation refuses to overwrite a drop-in created concurrently.
  os.link(tmp,target)
 finally:Path(tmp).unlink(missing_ok=True)
 out['installed'].append({'unit':unit,'path':str(target),'previously_present':False,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'state_before':{k:props.get(k)for k in ('ActiveState','SubState','InvocationID')}})
subprocess.run(['systemctl','daemon-reload'],check=True)
for unit in [r['unit']for r in out['installed']]+out['already_installed']:
 props=show(unit,'Environment','ActiveState','SubState','InvocationID');env=environment(props)
 actual={key:env.get(key)for key in expected};verified=actual==expected
 out['verification'].append({'unit':unit,'effective_credential_settings':actual,'verified':verified,'state_after':{k:props.get(k)for k in ('ActiveState','SubState','InvocationID')}})
out['failed_services']=subprocess.run(['systemctl','list-units','--failed','optima-*','constellation-*','--no-pager','--no-legend'],capture_output=True,text=True,check=True).stdout
out['finished_at']=datetime.now(timezone.utc).isoformat();out['status']='applied_and_verified'if all(v['verified']for v in out['verification'])else'verification_failed'
out['activation_note']='No services restarted; running processes inherit settings on their next normal scheduled start.'
import boto3
receipt_key='research-data/constellation-backfill/repairs/entries-62-75-20261114/preventive-service-role-rollout-receipt.json'
boto3.client('s3',region_name='us-east-1').put_object(Bucket='data-collection-059416028963-us-east-1-an',Key=receipt_key,Body=json.dumps(out).encode(),ServerSideEncryption='AES256')
print(json.dumps({'receipt_key':receipt_key}))
'''.replace('__APPROVED_PLAN__',repr(plan)).replace('__PLAN_SHA__',repr(hashlib.sha256(raw).hexdigest()))
response=remote(T3,code);pointer=json.loads(response['out']);receipt=json.loads(session.client('s3').get_object(Bucket=B,Key=pointer['receipt_key'])['Body'].read());receipt['ssm_command_id']=response['command']
path=P/'preventive-service-role-rollout-receipt.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
s=session.client('s3');s.put_object(Bucket=B,Key=BASE+path.name,Body=path.read_bytes(),ServerSideEncryption='AES256')
print(json.dumps({'status':receipt['status'],'installed':len(receipt['installed']),'already_installed':len(receipt['already_installed']),'skipped':receipt['skipped'],'verified':sum(v['verified']for v in receipt['verification']),'failed_services':receipt['failed_services'],'restarts':receipt['service_restarts_requested']}),flush=True)
assert receipt['status']=='applied_and_verified'
report_path=P/'review-complete.json';report=json.loads(report_path.read_text());report['optional_preventive_credentials']={'status':receipt['status'],'owner_approved':True,'services_approved':44,'installed':len(receipt['installed']),'already_installed':len(receipt['already_installed']),'skipped':receipt['skipped'],'verified':len(receipt['verification']),'restarts':[],'receipt':path.name,'applied_at':receipt['finished_at'],'activation_note':receipt['activation_note']};report_path.write_text(json.dumps(report,indent=2)+'\n')
manifest_path=P/'review-artifact-manifest.json';manifest=json.loads(manifest_path.read_text())
for p in [path,report_path]:
 body=p.read_bytes();s.put_object(Bucket=B,Key=BASE+p.name,Body=body,ServerSideEncryption='AES256');manifest[p.name]={'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)}
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n');s.put_object(Bucket=B,Key=BASE+manifest_path.name,Body=manifest_path.read_bytes(),ServerSideEncryption='AES256')
body=s.get_object(Bucket=B,Key=BASE+path.name)['Body'].read();assert hashlib.sha256(body).hexdigest()==manifest[path.name]['sha256']
print('Rollout receipt and updated review archived and read back successfully.',flush=True)
