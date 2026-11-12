import base64,json,hashlib
from pathlib import Path
import boto3
p=Path(__file__).parent;c=json.loads(Path('config/constellation-infrastructure.json').read_text());s=boto3.client('s3',region_name=c['region']);files={}
for name in ('metadata_engine/mhra.py','metadata_engine/source_policies.py','metadata_engine/evidence.py'):
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key=c['prefix']+'/deployments/mhra-validation-20261110/'+sha+'/'+name;s.put_object(Bucket=c['bucket'],Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
script='''import boto3,hashlib,json,os,subprocess,time
from pathlib import Path
files=FILES;s=boto3.client('s3',region_name='us-east-1');root=Path('/opt/constellation/metadata-engine-runtime')
subprocess.run(['systemctl','stop','optima-metadata-worker.timer'],check=True)
try:
 deadline=time.monotonic()+300
 while subprocess.run(['systemctl','is-active','--quiet','optima-metadata-worker.service']).returncode==0 or subprocess.check_output(['systemctl','show','optima-metadata-worker.service','-p','ActiveState','--value'],text=True).strip()=='activating':
  if time.monotonic()>deadline:raise RuntimeError('worker_not_idle')
  time.sleep(3)
 for name,meta in files.items():
  raw=s.get_object(Bucket=BUCKET,Key=meta['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==meta['sha256'];compile(raw,name,'exec')
  target=root/name;backup=Path('/opt/constellation/tmp/mhra-metadata1110-backup')/name;backup.parent.mkdir(parents=True,exist_ok=True)
  if target.exists() and not backup.exists():backup.write_bytes(target.read_bytes())
  temp=target.with_suffix('.repair.tmp');temp.write_bytes(raw);os.chmod(temp,0o644);temp.replace(target)
 config=root/'config/metadata-engine.json';data=json.loads(config.read_text());data['contracts']['uk_mhra']=POLICY;data.setdefault('verified_source_failure_handling',{})['uk_mhra']='queue_by_source_date';data['build_sha256']=hashlib.sha256(b''.join(x.read_bytes()for x in sorted((root/'metadata_engine').glob('*.py')))+(root/'hkex_originals.py').read_bytes()).hexdigest();temp=config.with_suffix('.repair.tmp');temp.write_text(json.dumps(data,indent=2)+'\\n');temp.replace(config)
 print(json.dumps({'updated_files':list(files),'build_sha256':data['build_sha256']}),flush=True)
finally:subprocess.run(['systemctl','enable','--now','optima-metadata-worker.timer'],check=True)
'''.replace('POLICY',repr(json.load(open('config/metadata-engine.json'))['contracts']['uk_mhra'])).replace('FILES',repr(files)).replace('BUCKET',repr(c['bucket']))
encoded=base64.b64encode(script.encode()).decode();cmd="/opt/constellation/legacy-venv/bin/python -c \"import base64;exec(base64.b64decode('"+encoded+"'))\""
r=boto3.client('ssm',region_name=c['region']).send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=420)
(p/'metadata-deployment.json').write_text(json.dumps({'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id'],'files':files},indent=2));print(r['Command']['CommandId'])
