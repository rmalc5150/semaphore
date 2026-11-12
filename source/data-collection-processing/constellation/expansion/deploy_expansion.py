"""Deploy reviewed source-specific history routes without touching daily capture."""
import hashlib,io,json,shlex,tarfile
from pathlib import Path
from constellation.control import Control
from constellation.deploy_legacy import dependencies
ROOT=Path(__file__).resolve().parents[2]

def main():
    c=Control();routes=json.loads((ROOT/'config/constellation-legacy-routes.json').read_text())['routes']
    modules=dependencies([r['argv'][0] for r in routes]);bundle=ROOT/'constellation/expansion/deploy.tar.gz'
    with tarfile.open(bundle,'w:gz') as archive:
        def add(name,body):
            if isinstance(body,str):body=body.encode()
            info=tarfile.TarInfo(name);info.size=len(body);info.mode=0o644;archive.addfile(info,io.BytesIO(body))
        for name,body in modules.items():add('source/'+name,body)
        for path in (ROOT/'config').glob('*.json'):
            if path.name=='constellation-infrastructure.json' or not path.is_file():continue
            add('source/config/'+path.name,path.read_bytes())
        for name in ('control.py','shared_limits.py','legacy_routes.py','legacy_worker.py','worker.py','sources.py','gaps.py','coverage_scope.py'):
            add('constellation/'+name,(ROOT/'constellation'/name).read_bytes())
            if name in ('control.py','shared_limits.py','legacy_routes.py','gaps.py'):add('source/constellation/'+name,(ROOT/'constellation'/name).read_bytes())
        add('config/constellation-legacy-routes.json',(ROOT/'config/constellation-legacy-routes.json').read_bytes())
        add('constellation/constellation-legacy-worker@.service',(ROOT/'constellation/constellation-legacy-worker@.service').read_bytes())
    digest=hashlib.sha256(bundle.read_bytes()).hexdigest();key=c.config['prefix']+'/deployments/expansion-'+digest+'.tar.gz';c.s3.upload_file(str(bundle),c.config['bucket'],key,ExtraArgs={'ServerSideEncryption':'AES256'})
    for row in routes:
        if not (row['execution_enabled'] or row.get('activation_staged')):continue
        target=c.config['prefix']+'/legacy-runtime/'+row['unit']+'/current.json'
        try:c.s3.head_object(Bucket=c.config['bucket'],Key=target)
        except c.s3.exceptions.ClientError as e:
            if e.response['Error']['Code'] not in ('404','NoSuchKey'):raise
            c.s3.copy_object(Bucket=c.config['bucket'],Key=target,CopySource={'Bucket':c.config['bucket'],'Key':c.config['legacy_seed_key']},ServerSideEncryption='AES256')
    script='''set -eu
systemctl stop 'constellation-legacy-worker@*.service'
trap 'systemctl start constellation-legacy-worker@{1..8}.service' EXIT
cd /opt/constellation
aws s3 cp BUNDLE tmp/expansion.tar.gz --region us-east-1 --only-show-errors
echo 'DIGEST  tmp/expansion.tar.gz' | sha256sum --check --status
tar -xzf tmp/expansion.tar.gz --no-same-owner
/opt/constellation/.venv/bin/python - <<'WORKSPACES'
import os,json,uuid,hashlib
from datetime import datetime,timezone
import boto3
from pathlib import Path
base=Path('/opt/constellation');s3=boto3.client('s3',region_name='us-east-1');bucket='data-collection-059416028963-us-east-1-an'
rows=json.loads((base/'config/constellation-legacy-routes.json').read_text())['routes']
for row in rows:
 if not (row['execution_enabled'] or row.get('activation_staged')):continue
 root=base/'legacy'/row['unit'];root.mkdir(parents=True,exist_ok=True)
 ram=Path('/dev/shm/constellation-legacy')/row['unit'];(ram/'locks').mkdir(parents=True,exist_ok=True)
 if row.get('specialist_source') or row.get('public_capture_source'):
  if (ram/'pending.json').exists():raise RuntimeError('Recover pending runtime before seed isolation: '+row['unit'])
  prefix='research-data/constellation-backfill/legacy-runtime/'+row['unit']
  response=s3.get_object(Bucket=bucket,Key=prefix+'/current.json');state=json.loads(response['Body'].read());response['Body'].close()
  paths={rel:value for rel,value in state['paths'].items() if rel in ('config/company-universe.v0.2.json','config/company-universe.v0.3.json','config/company-universe.v0.5.json') or value['key'].startswith(prefix+'/')}
  if paths!=state['paths']:
   state.update(paths=paths,unit=row['unit'],run_id='isolated-source-seed-'+uuid.uuid4().hex,checkpointed_at=datetime.now(timezone.utc).isoformat())
   body=(json.dumps(state,sort_keys=True)+'\\n').encode();immutable=prefix+'/manifests/'+state['run_id']+'.json'
   s3.put_object(Bucket=bucket,Key=immutable,Body=body,ServerSideEncryption='AES256',IfNoneMatch='*')
   verified=s3.get_object(Bucket=bucket,Key=immutable);check=verified['Body'].read();verified['Body'].close();assert check==body
   s3.put_object(Bucket=bucket,Key=prefix+'/current.json',Body=body,ServerSideEncryption='AES256',IfMatch=response['ETag'])
 for source in (base/'source').rglob('*'):
  if not source.is_file():continue
  target=root/source.relative_to(base/'source');target.parent.mkdir(parents=True,exist_ok=True)
  rewrite=source.suffix in ('.py','.json','.sql','.sh');body=source.read_text() if rewrite else ''
  if target.exists():target.unlink()
  if source.suffix=='.py' or '/home/ec2-user/data-collection-processing' in body:target.write_text(body.replace('/home/ec2-user/data-collection-processing',str(root)))
  else:os.link(source,target)
 link=root/'.venv'
 if not link.exists():link.symlink_to(base/'legacy-venv',target_is_directory=True)
 for name in ('reports','mlperf-evidence-cache','ted-package-cache','collection-output'):
  link=root/name
  if not link.is_symlink():link.symlink_to(ram/'work'/name,target_is_directory=True)
WORKSPACES
chown -R ec2-user:ec2-user legacy source /dev/shm/constellation-legacy
install -m 0644 constellation/constellation-legacy-worker@.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now constellation-legacy-worker@{1..8}.service
systemctl is-active constellation-legacy-worker@{1..8}.service constellation-backfill@{1..5}.service
systemctl show constellation-workers.slice -p CPUQuotaPerSecUSec -p MemoryMax -p MemoryCurrent
'''.replace('BUNDLE',shlex.quote('s3://'+c.config['bucket']+'/'+key)).replace('DIGEST',digest).replace('{1..8}','{1..'+str(c.config['worker_pool']['legacy_workers'])+'}').replace('{1..5}','{1..'+str(c.config['worker_pool']['raw_workers'])+'}')
    r=c.session.client('ssm').send_command(InstanceIds=[c.config['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':['bash -c '+shlex.quote(script)]},TimeoutSeconds=600)
    receipt={'command_id':r['Command']['CommandId'],'bundle_sha256':digest,'source_modules':len(modules),'enabled_historical_routes':sum(r['execution_enabled'] and r['route_kind']!='migration_probe' for r in routes),'collection_enabled':True,'daily_capture_touched':False}
    (ROOT/'constellation/expansion/deployment.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':main()
