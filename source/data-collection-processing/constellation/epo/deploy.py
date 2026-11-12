"""Deploy only EPO additions; retain existing pools and the NICE pause."""
import base64,hashlib,json,shlex,time
from pathlib import Path
from constellation.control import Control
ROOT=Path(__file__).resolve().parents[2]
SOURCE='epo_ops_patent_legal_events';UNIT='constellation-specialist-'+SOURCE+'.service'

def main():
 c=Control();objects={}
 for name in ('epo_ops.py','additional_source_apis.py','additional_source_plan.py','specialist_inputs.py','constellation/epo/bootstrap.py','config/constellation-specialist-historical.json','config/constellation-legacy-routes.json'):
  body=(ROOT/name).read_bytes();sha=hashlib.sha256(body).hexdigest();key=c.config['prefix']+'/deployments/epo-'+sha+'/'+name;c.s3.put_object(Bucket=c.config['bucket'],Key=key,Body=body,ServerSideEncryption='AES256');objects[name]={'key':key,'sha256':sha}
 response=c.s3.get_object(Bucket=c.config['bucket'],Key=c.config['legacy_seed_key']);seed=json.loads(response['Body'].read());response['Body'].close();seed['paths']={k:v for k,v in seed['paths'].items() if k in ('config/company-universe.v0.2.json','config/company-universe.v0.3.json','config/company-universe.v0.5.json')};seed['unit']=UNIT;seed['run_id']='epo-source-seed';prefix=c.config['prefix']+'/legacy-runtime/'+UNIT
 try:c.s3.put_object(Bucket=c.config['bucket'],Key=prefix+'/current.json',Body=json.dumps(seed).encode(),ServerSideEncryption='AES256',IfNoneMatch='*')
 except c.s3.exceptions.ClientError as e:
  if e.response['Error']['Code'] not in ('PreconditionFailed','412'):raise
 code=r'''import boto3,hashlib,json,os
from pathlib import Path
base=Path('/opt/constellation');s3=boto3.client('s3',region_name='us-east-1');unit=UNIT
for name,obj in OBJECTS.items():
 response=s3.get_object(Bucket=BUCKET,Key=obj['key']);body=response['Body'].read();response['Body'].close();assert hashlib.sha256(body).hexdigest()==obj['sha256']
 if name=='config/constellation-legacy-routes.json':targets=[base/name,base/'source'/name]
 elif name=='constellation/epo/bootstrap.py':targets=[base/'source'/'epo_bootstrap.py']
 elif name.startswith('config/'):targets=[base/'source'/name,base/'legacy'/unit/name]
 else:targets=[base/'source'/name,*[p/name for p in (base/'legacy').iterdir() if p.is_dir()]]
 for target in targets:
  target.parent.mkdir(parents=True,exist_ok=True);tmp=target.with_suffix('.epo-new');tmp.write_text(body.decode().replace('/home/ec2-user/data-collection-processing',str(target.parent if '/' not in name else base/'source')));os.chown(tmp,1000,1000);tmp.replace(target)
root=base/'legacy'/unit;root.mkdir(parents=True,exist_ok=True);ram=Path('/dev/shm/constellation-legacy')/unit;(ram/'locks').mkdir(parents=True,exist_ok=True)
for source in (base/'source').rglob('*'):
 if not source.is_file():continue
 target=root/source.relative_to(base/'source');target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists():continue
 body=source.read_bytes()
 if source.suffix in ('.py','.json','.sql','.sh'):
  target.write_text(body.decode().replace('/home/ec2-user/data-collection-processing',str(root)).replace(str(base/'source'),str(root)))
 else:target.write_bytes(body)
 os.chown(target,1000,1000)
if not (root/'.venv').exists():(root/'.venv').symlink_to(base/'legacy-venv',target_is_directory=True)
for name in ('reports','mlperf-evidence-cache','ted-package-cache','collection-output'):
 p=root/name
 if not p.is_symlink():p.symlink_to(ram/'work'/name,target_is_directory=True)
for p in [root,*root.rglob('*'),ram,ram/'locks']:
 if not p.is_symlink():os.chown(p,1000,1000)
# Enable only after isolated source/runtime/configuration are present.
for p in (base/'config/constellation-legacy-routes.json',base/'source/config/constellation-legacy-routes.json',root/'config/constellation-legacy-routes.json'):
 d=json.loads(p.read_text());r=next(r for r in d['routes'] if r['unit']==unit);r.update(execution_enabled=True,activation_staged=False);tmp=p.with_suffix('.epo-new');tmp.write_text(json.dumps(d,indent=2));os.chown(tmp,1000,1000);tmp.replace(p)
assert next(r for r in json.loads((base/'config/constellation-legacy-routes.json').read_text())['routes'] if r.get('catalog_entry')==88)['execution_enabled'] is False
print(json.dumps({'unit':unit,'workspace_ready':root.is_dir(),'route_enabled':True,'NICE_remains_paused':True,'pools_restarted':False}))
'''.replace('OBJECTS',repr(objects)).replace('BUCKET',repr(c.config['bucket'])).replace('UNIT',repr(UNIT))
 compile(code,'epo_deploy','exec')
 command='/opt/constellation/.venv/bin/python -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(base64.b64encode(code.encode()).decode())+'))')
 s=c.session.client('ssm');identity=s.send_command(InstanceIds=[c.config['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[command]},TimeoutSeconds=180)['Command']['CommandId']
 receipt={'command_id':identity,'files':objects,'unit':UNIT};(ROOT/'constellation/epo/deployment.json').write_text(json.dumps(receipt,indent=2)+'\n');print(identity)
if __name__=='__main__':main()
