import boto3,json,hashlib,base64,time
from pathlib import Path
p=Path(__file__).parent;c=json.load(open('config/constellation-infrastructure.json'));s=boto3.client('s3',region_name=c['region']);files={}
for name in ('cms_payments_resumed.py','cms_financial_collection.py','config/cms-financial-resumed.json','config/cms-financial-collection.json','config/cms-financial-resumed-editions.json'):
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key=c['prefix']+'/deployments/cms-payments-20261111/'+sha+'/'+name;s.put_object(Bucket=c['bucket'],Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
checkpoint=json.loads(s.get_object(Bucket=c['bucket'],Key='research-data/constellation-backfill/legacy-runtime/optima-cms-financial-collection.service/current.json')['Body'].read());bootstrap=checkpoint['paths']['cms-financial-backfill-2026-10-16.sqlite3'];raw=s.get_object(Bucket=c['bucket'],Key=bootstrap['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==bootstrap['sha256']and len(raw)==bootstrap['bytes'];staged_key=c['prefix']+'/deployments/cms-payments-20261111/'+bootstrap['sha256']+'/registry.sqlite3';s.put_object(Bucket=c['bucket'],Key=staged_key,Body=raw,ServerSideEncryption='AES256');bootstrap={**bootstrap,'staged_key':staged_key}
name='optima-cms-payments-resumed'
unit='[Unit]\nDescription=Bounded CMS catalog capture and metadata handoff\nAfter=network-online.target\n[Service]\nType=oneshot\nUser=ec2-user\nWorkingDirectory=/opt/constellation/source\nExecStart=/opt/constellation/legacy-venv/bin/python -B cms_payments_resumed.py --mode catalog\nSlice=constellation-workers.slice\nMemoryMax=536870912\nMemorySwapMax=0\nCPUQuota=25%\nTimeoutStartSec=360\nEnvironment=CONSTELLATION_SHARED_HTTP_LIMITS=1\nEnvironment=CONSTELLATION_ROLE=worker\n'
timer='[Unit]\nDescription=Continue CMS financial collection and daily catalog discovery\n[Timer]\nOnBootSec=120\nOnUnitInactiveSec=300\nPersistent=true\nUnit='+name+'.service\n[Install]\nWantedBy=timers.target\n'
units={name+'.service':unit,name+'.timer':timer}
for n,b in units.items():(p/n).write_text(b)
script='''import boto3,hashlib,os,json,subprocess,sqlite3
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');root=Path('/opt/constellation/source')
for name,ref in FILES.items():
 raw=s.get_object(Bucket=BUCKET,Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256']
 if name.endswith('.py'):compile(raw,name,'exec')
 target=root/name;target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_suffix('.cms.tmp');temp.write_bytes(raw);temp.replace(target)
state=Path('/opt/constellation/state/cms-financial/registry.sqlite3');state.parent.mkdir(parents=True,exist_ok=True);os.chown(state.parent,1000,1000)
if not state.exists():
 checkpoint=json.loads(s.get_object(Bucket=BUCKET,Key='research-data/constellation-backfill/legacy-runtime/optima-cms-financial-collection.service/current.json')['Body'].read());ref=checkpoint['paths']['cms-financial-backfill-2026-10-16.sqlite3'];assert ref['sha256']==BOOTSTRAP['sha256'];raw=s.get_object(Bucket=BUCKET,Key=BOOTSTRAP['staged_key'])['Body'].read();assert len(raw)==ref['bytes']and hashlib.sha256(raw).hexdigest()==ref['sha256'];temp=state.with_suffix('.restore.tmp');temp.write_bytes(raw)
 with sqlite3.connect(temp)as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok';print(json.dumps({'restored_statuses':db.execute('SELECT status,count(*) FROM editions GROUP BY status').fetchall()}),flush=True)
 os.chown(temp,1000,1000);temp.replace(state)
cfg=root/'config/specialist-inputs.json';plan=json.loads(cfg.read_text())
for source in plan['sources']:
 if source['source']=='cms_payments_catalog':
  source['execution_lane']='cms_payments';source['coverage_note']='Original dataset descriptors and edition/download identities only; payment and spending rows are captured separately in optima_collected_data.cms_open_payments_rows and cms_drug_spending_rows.'
cfg.write_text(json.dumps(plan,indent=2)+chr(10))
for name,body in UNITS.items():Path('/etc/systemd/system/'+name).write_text(body)
subprocess.run(['systemctl','daemon-reload'],check=True);subprocess.run(['systemctl','enable','--now','optima-cms-payments-resumed.timer'],check=True);subprocess.run(['systemctl','start','--no-block','optima-cms-payments-resumed.service'],check=True)
'''.replace('FILES',repr(files)).replace('BUCKET',repr(c['bucket'])).replace('UNITS',repr(units)).replace('BOOTSTRAP',repr(bootstrap))
enc=base64.b64encode(script.encode()).decode();cmd='/opt/constellation/legacy-venv/bin/python -c "import base64;exec(base64.b64decode(\''+enc+'\'))"';ssm=boto3.client('ssm',region_name=c['region']);r=ssm.send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=90);ref={'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id']};(p/'capture-deployment.json').write_text(json.dumps(ref,indent=2))
for _ in range(75):
 try:o=ssm.get_command_invocation(CommandId=ref['command_id'],InstanceId=ref['instance'])
 except ssm.exceptions.InvocationDoesNotExist:time.sleep(1);continue
 if o['Status']not in ('Pending','InProgress','Delayed'):break
 time.sleep(1)
(p/'capture-deployment-result.json').write_text(json.dumps(o,indent=2,default=str));print(o['Status'],o['StandardOutputContent'],o['StandardErrorContent']);assert o['Status']=='Success'
