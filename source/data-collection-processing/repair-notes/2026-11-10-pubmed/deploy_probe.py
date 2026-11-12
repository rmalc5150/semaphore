import base64,json,hashlib,boto3
from pathlib import Path
p=Path(__file__).parent;c=json.load(open('config/constellation-infrastructure.json'));s=boto3.client('s3',region_name=c['region']);files={}
for name in ('pubmed_capture_probe.py','pubmed_enrichment.py','metadata_engine/pubmed_enrichment.py'):
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key=c['prefix']+'/deployments/pubmed-probe-20261110/'+sha+'/'+name;s.put_object(Bucket=c['bucket'],Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
script='''import boto3,hashlib,subprocess
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');root=Path('/opt/constellation/source')
for name,ref in FILES.items():
 raw=s.get_object(Bucket=BUCKET,Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];compile(raw,name,'exec');target=root/name;target.parent.mkdir(parents=True,exist_ok=True);backup=Path('/opt/constellation/tmp/pubmed-probe-backup')/name;backup.parent.mkdir(parents=True,exist_ok=True)
 if target.exists()and not backup.exists():backup.write_bytes(target.read_bytes())
 temp=target.with_suffix('.repair.tmp');temp.write_bytes(raw);temp.chmod(0o644);temp.replace(target)
subprocess.run(['systemd-run','--unit=optima-pubmed-verified-capture','--property=User=ec2-user','--property=WorkingDirectory=/opt/constellation/source','--property=Slice=constellation-workers.slice','--property=MemoryMax=268435456','--property=CPUQuota=20%','--property=RuntimeMaxSec=240','--setenv=CONSTELLATION_ROLE=worker','--setenv=CONSTELLATION_SHARED_HTTP_LIMITS=1','/opt/constellation/legacy-venv/bin/python','-B','pubmed_capture_probe.py'],check=True)
'''.replace('FILES',repr(files)).replace('BUCKET',repr(c['bucket']));enc=base64.b64encode(script.encode()).decode();cmd='/opt/constellation/legacy-venv/bin/python -c "import base64;exec(base64.b64decode(\''+enc+'\'))"';r=boto3.client('ssm',region_name=c['region']).send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=60);(p/'capture-deployment.json').write_text(json.dumps({'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id']},indent=2));print(r['Command']['CommandId'])
