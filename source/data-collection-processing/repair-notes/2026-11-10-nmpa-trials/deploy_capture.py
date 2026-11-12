import boto3,json,hashlib,base64
from pathlib import Path
p=Path(__file__).parent;c=json.load(open('config/constellation-infrastructure.json'));s=boto3.client('s3',region_name=c['region']);index=json.loads(s.get_object(Bucket=c['bucket'],Key='research-data/operations/s3-runtime/current.json')['Body'].read());seed=index['paths']['nmpa-enrichment-backfill-2026-10-16.sqlite3'];seedkey=c['prefix']+'/deployments/nmpa-resumed-20261110/'+seed['sha256']+'/backfill-seed.sqlite3';s.copy_object(Bucket=c['bucket'],Key=seedkey,CopySource={'Bucket':c['bucket'],'Key':seed['key']},ServerSideEncryption='AES256');cfg=json.load(open('config/nmpa-enrichment-backfill.json'));cfg.update(seed={'bucket':c['bucket'],'key':seedkey,'sha256':seed['sha256'],'bytes':seed['bytes']},seed_inventory_pages=len(json.load(open(p/'inventory-head-before.json'))['pages']));cfg.pop('email_topic_arn',None);cfg.pop('email_recipient',None);Path('config/nmpa-resumed-worker.json').write_text(json.dumps(cfg,indent=2)+'\n');files={}
for name in ('nmpa_resumed_capture.py','nmpa_drug_trials.py','nmpa_enrichment.py','nmpa_enrichment_worker.py','nmpa_baseline.py','metadata_engine/nmpa_tables.py','config/nmpa-resumed-worker.json'):
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key=c['prefix']+'/deployments/nmpa-resumed-20261110/'+sha+'/'+name;s.put_object(Bucket=c['bucket'],Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
units={}
for mode,delay in [('inventory',300),('details',120)]:
 name='optima-nmpa-resumed-'+mode;unit='[Unit]\nDescription=Bounded NMPA '+mode+' capture from saved checkpoints\nAfter=network-online.target\n[Service]\nType=oneshot\nUser=ec2-user\nWorkingDirectory=/opt/constellation/source\nExecStart=/opt/constellation/legacy-venv/bin/python -B nmpa_resumed_capture.py '+mode+'\nSlice=constellation-workers.slice\nMemoryMax=536870912\nMemorySwapMax=0\nCPUQuota=20%\nTimeoutStartSec=300\nEnvironment=CONSTELLATION_ROLE=worker\nEnvironment=CONSTELLATION_SHARED_HTTP_LIMITS=1\n';timer='[Unit]\nDescription=Continue NMPA '+mode+' capture\n[Timer]\nOnBootSec=120\nOnUnitInactiveSec='+str(delay)+'\nPersistent=true\nUnit='+name+'.service\n[Install]\nWantedBy=timers.target\n';units[name+'.service']=unit;units[name+'.timer']=timer
for name,body in units.items():(p/name).write_text(body)
script='''import boto3,json,hashlib,subprocess
from pathlib import Path
root=Path('/opt/constellation/source');s=boto3.client('s3',region_name='us-east-1')
for name,ref in FILES.items():
 raw=s.get_object(Bucket=BUCKET,Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
 if name.endswith('.py'):compile(raw,name,'exec')
 else:json.loads(raw)
 backup=Path('/opt/constellation/tmp/nmpa-resumed-backup')/name;backup.parent.mkdir(parents=True,exist_ok=True)
 if target.exists() and not backup.exists():backup.write_bytes(target.read_bytes())
 temp=target.with_suffix('.repair.tmp');temp.write_bytes(raw);temp.chmod(0o644);temp.replace(target)
for name,body in UNITS.items():Path('/etc/systemd/system',name).write_text(body)
subprocess.run(['systemctl','daemon-reload'],check=True)
for mode in ('inventory','details'):
 subprocess.run(['systemctl','enable','--now','optima-nmpa-resumed-'+mode+'.timer'],check=True)
 subprocess.run(['systemctl','start','--no-block','optima-nmpa-resumed-'+mode+'.service'],check=True)
print(json.dumps({'installed_units':list(UNITS),'files':list(FILES)}))
'''.replace('FILES',repr(files)).replace('BUCKET',repr(c['bucket'])).replace('UNITS',repr(units));enc=base64.b64encode(script.encode()).decode();cmd='/opt/constellation/legacy-venv/bin/python -c "import base64;exec(base64.b64decode(\''+enc+'\'))"';r=boto3.client('ssm',region_name=c['region']).send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=60);(p/'capture-deployment.json').write_text(json.dumps({'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id'],'seed':cfg['seed'],'files':files},indent=2));print(r['Command']['CommandId'])
