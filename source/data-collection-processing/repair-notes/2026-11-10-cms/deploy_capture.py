import boto3,json,hashlib,base64,time
from pathlib import Path
p=Path(__file__).parent;c=json.load(open('config/constellation-infrastructure.json'));s=boto3.client('s3',region_name=c['region']);files={}
for name in ['cms_coverage_capture.py','specialist_inputs.py']:
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key=c['prefix']+'/deployments/cms-coverage-capture-20261110/'+sha+'/'+name;s.put_object(Bucket=c['bucket'],Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
units={}
for mode in ('discover','capture'):
 name='optima-cms-coverage-'+mode
 unit='[Unit]\nDescription=Bounded CMS NCD coverage '+mode+'\nAfter=network-online.target\n[Service]\nType=oneshot\nUser=ec2-user\nWorkingDirectory=/opt/constellation/source\nExecStart=/opt/constellation/legacy-venv/bin/python -B cms_coverage_capture.py --mode '+mode+'\nSlice=constellation-workers.slice\nMemoryMax=402653184\nMemorySwapMax=0\nCPUQuota=20%\nTimeoutStartSec=300\nEnvironment=CONSTELLATION_SHARED_HTTP_LIMITS=1\nEnvironment=CONSTELLATION_ROLE=worker\n'
 timer='[Unit]\nDescription=Continue CMS NCD coverage '+mode+'\n[Timer]\nOnBootSec=120\nOnUnitInactiveSec=120\nPersistent=true\nUnit='+name+'.service\n[Install]\nWantedBy=timers.target\n'
 units[name+'.service']=unit;units[name+'.timer']=timer
 (p/(name+'.service')).write_text(unit);(p/(name+'.timer')).write_text(timer)
script='''import boto3,hashlib,subprocess
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');root=Path('/opt/constellation/source')
for name,ref in FILES.items():
 raw=s.get_object(Bucket=BUCKET,Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];compile(raw,name,'exec');target=root/name;target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_suffix('.cms.tmp');temp.write_bytes(raw);temp.replace(target)
import json
cfg=root/'config/specialist-inputs.json';plan=json.loads(cfg.read_text())
for source in plan['sources']:
 if source['source']=='cms_coverage':source['execution_lane']='cms_discovery'
cfg.write_text(json.dumps(plan,indent=2)+chr(10))
import sys
sys.path.insert(0,str(root))
import time
expiry=time.monotonic()+300
while any(subprocess.check_output(['systemctl','show','optima-cms-coverage-'+mode+'.service','-p','ActiveState','--value'],text=True).strip() in ('active','activating')for mode in ('discover','capture')):
 if time.monotonic()>expiry:raise RuntimeError('cms_capture_not_idle_for_checkpoint_repair')
 time.sleep(3)
from collection_storage import StorageSettings
from cms_coverage_capture import BASE,save_state,load_state
from window_publication import list_keys
settings=StorageSettings.load(root/'config/collection-storage.s3.json');store=settings.store()
for key in list_keys(store,settings,BASE+'outcomes/'):
 value=load_state(store,key)
 if value.get('reason')=="ModuleNotFoundError: No module named 'metadata_engine.runtime_db'":
  value['retry_after']=0;save_state(store,key,value)
key=BASE+'discovery-state.json';state=load_state(store,key)
for value in state.get('parents',{}).values():
 if value.get('reason')=="ModuleNotFoundError: No module named 'metadata_engine.runtime_db'":value['retry_after']=0
save_state(store,key,state)
key=BASE+'capture-state.json';state=load_state(store,key);state['cursor']='';save_state(store,key,state)
for name,body in UNITS.items():Path('/etc/systemd/system/'+name).write_text(body)
subprocess.run(['systemctl','daemon-reload'],check=True)
for mode in ('discover','capture'):
 name='optima-cms-coverage-'+mode
 subprocess.run(['systemctl','enable','--now',name+'.timer'],check=True)
 subprocess.run(['systemctl','start','--no-block',name+'.service'],check=True)
'''.replace('FILES',repr(files)).replace('BUCKET',repr(c['bucket'])).replace('UNITS',repr(units))
enc=base64.b64encode(script.encode()).decode();cmd='/opt/constellation/legacy-venv/bin/python -c "import base64;exec(base64.b64decode(\''+enc+'\'))"';a=boto3.client('ssm',region_name=c['region']);r=a.send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=420);ref={'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id']};(p/'capture-deployment.json').write_text(json.dumps(ref,indent=2))
for _ in range(210):
 try:out=a.get_command_invocation(CommandId=ref['command_id'],InstanceId=ref['instance'])
 except a.exceptions.InvocationDoesNotExist:time.sleep(1);continue
 if out['Status'] not in ('Pending','InProgress','Delayed'):break
 time.sleep(1)
(p/'capture-deployment-result.json').write_text(json.dumps(out,indent=2,default=str));print(out['Status'],out.get('StandardErrorContent',''));assert out['Status']=='Success'
