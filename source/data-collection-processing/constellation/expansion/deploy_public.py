"""Install staged public routes before permitting the controller to dispatch them."""
import hashlib,io,json,shlex,tarfile,uuid
from pathlib import Path
from constellation.control import Control
ROOT=Path(__file__).resolve().parents[2]

def main():
    c=Control();prior=json.loads((ROOT/'constellation/expansion/deployment.json').read_text())
    status=c.session.client('ssm').get_command_invocation(CommandId=prior['command_id'],InstanceId=c.config['worker_instance_id'])['Status']
    if status!='Success':raise RuntimeError('Earlier staging must finish successfully before activation: '+status)
    config=json.loads((ROOT/'config/constellation-legacy-routes.json').read_text())
    public_native={r['source'] for r in json.loads((ROOT/'constellation/expansion/new-adapters.json').read_text()) if r['adapter'] not in ('fred','dart')}
    selected=[r for r in config['routes'] if r.get('public_capture_source') or r.get('specialist_source') in public_native]
    for row in selected:row.update(execution_enabled=True,activation_staged=False,remaining_requirements=[])
    activation=ROOT/'constellation/expansion/public-routes.ACTIVATE.json';activation.write_text(json.dumps(config,indent=2)+'\n')
    seed_response=c.s3.get_object(Bucket=c.config['bucket'],Key=c.config['legacy_seed_key']);seed=json.loads(seed_response['Body'].read());seed_response['Body'].close()
    created=0
    for row in selected:
        prefix=c.config['prefix']+'/legacy-runtime/'+row['unit'];key=prefix+'/current.json'
        try:c.s3.head_object(Bucket=c.config['bucket'],Key=key)
        except c.s3.exceptions.ClientError as e:
            if e.response['Error']['Code'] not in ('404','NoSuchKey'):raise
            state={**seed,'paths':{k:v for k,v in seed['paths'].items() if k in ('config/company-universe.v0.2.json','config/company-universe.v0.3.json','config/company-universe.v0.5.json')},'unit':row['unit'],'run_id':'public-seed-'+uuid.uuid4().hex}
            body=json.dumps(state,sort_keys=True).encode()
            for target in (prefix+'/manifests/'+state['run_id']+'.json',key):c.s3.put_object(Bucket=c.config['bucket'],Key=target,Body=body,ServerSideEncryption='AES256',IfNoneMatch='*')
            created+=1
    bundle=ROOT/'constellation/expansion/public-deploy.tar.gz'
    with tarfile.open(bundle,'w:gz') as archive:
        for name in ('provider_publication.py','public_source_capture.py','constellation/s3_integrity.py','specialist_inputs.py','additional_source_apis.py','additional_source_plan.py'):
            archive.add(ROOT/name,arcname='source/'+name,recursive=False)
        for name in ('constellation-public-sources.json','constellation-specialist-historical.json','specialist-inputs.json'):
            archive.add(ROOT/'config'/name,arcname='source/config/'+name,recursive=False)
        archive.add(activation,arcname='public-routes.json',recursive=False)
    digest=hashlib.sha256(bundle.read_bytes()).hexdigest();key=c.config['prefix']+'/deployments/public-'+digest+'.tar.gz'
    c.s3.upload_file(str(bundle),c.config['bucket'],key,ExtraArgs={'ServerSideEncryption':'AES256'})
    script=r'''set -eu
cd /opt/constellation
aws s3 cp BUNDLE tmp/public-deploy.tar.gz --region us-east-1 --only-show-errors
echo 'DIGEST  tmp/public-deploy.tar.gz' | sha256sum --check --status
tar -xzf tmp/public-deploy.tar.gz --no-same-owner
/opt/constellation/.venv/bin/python - <<'WORKSPACES'
import json,os,shutil
from pathlib import Path
base=Path('/opt/constellation');rows=json.loads((base/'public-routes.json').read_text())['routes']
selected=[r for r in rows if r.get('public_capture_source') or (r.get('catalog_entry') in (76,143,145,147,156) and r.get('specialist_source'))]
for row in selected:
 root=base/'legacy'/row['unit'];new=not root.exists();root.mkdir(parents=True,exist_ok=True)
 ram=Path('/dev/shm/constellation-legacy')/row['unit'];(ram/'locks').mkdir(parents=True,exist_ok=True)
 names=list((base/'source').rglob('*')) if new else [base/'source'/n for n in ('provider_publication.py','public_source_capture.py','constellation/s3_integrity.py','specialist_inputs.py','additional_source_apis.py','additional_source_plan.py','config/constellation-public-sources.json','config/constellation-specialist-historical.json','config/specialist-inputs.json')]
 for source in names:
  if not source.is_file():continue
  target=root/source.relative_to(base/'source');target.parent.mkdir(parents=True,exist_ok=True)
  if target.exists():target.unlink()
  if source.suffix in ('.py','.json','.sh','.sql'):
   target.write_text(source.read_text().replace('/home/ec2-user/data-collection-processing',str(root)))
  else:shutil.copyfile(source,target)
 link=root/'.venv'
 if not link.exists():link.symlink_to(base/'legacy-venv',target_is_directory=True)
 for name in ('reports','mlperf-evidence-cache','ted-package-cache','collection-output'):
  link=root/name
  if not link.is_symlink():link.symlink_to(ram/'work'/name,target_is_directory=True)
 print(json.dumps({'prepared_public_route':row['unit']}),flush=True)
target=base/'config/constellation-legacy-routes.json';temporary=target.with_suffix('.new');temporary.write_bytes((base/'public-routes.json').read_bytes());temporary.replace(target)
print(json.dumps({'enabled_historical_routes':sum(r['execution_enabled'] and r['route_kind']!='migration_probe' for r in rows),'public_routes_ready':len(selected)}))
WORKSPACES
chown -R ec2-user:ec2-user legacy source /dev/shm/constellation-legacy
systemctl is-active constellation-legacy-worker@{1..8}.service constellation-backfill@{1..5}.service
'''.replace('BUNDLE',shlex.quote('s3://'+c.config['bucket']+'/'+key)).replace('DIGEST',digest)
    command=c.session.client('ssm').send_command(InstanceIds=[c.config['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':['bash -c '+shlex.quote(script)]},TimeoutSeconds=600)['Command']['CommandId']
    receipt={'command_id':command,'bundle_sha256':digest,'public_archive_routes':sum(bool(r.get('public_capture_source')) for r in selected),'public_native_routes':len(public_native),'new_runtime_seeds':created,'controller_activation_pending':True}
    (ROOT/'constellation/expansion/public-deployment.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':main()
