"""Package reviewed legacy dependencies and isolated state roots; leave work paused."""
import ast
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile

import boto3
from constellation.control import Control

ROOT=Path(__file__).resolve().parents[1]


def dependencies(scripts):
    result={};pending=list(scripts)+['s3_runtime.py','s3_runtime_fs.py','sitecustomize.py']
    while pending:
        name=pending.pop()
        if name in result:continue
        path=ROOT/name
        if not path.is_file():raise ValueError('Missing collector dependency '+name)
        body=path.read_text();result[name]=body
        for node in ast.walk(ast.parse(body)):
            modules=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or ''] if isinstance(node,ast.ImportFrom) else []
            for module in modules:
                candidate=module.split('.')[0]+'.py'
                if (ROOT/candidate).is_file() and candidate not in result:pending.append(candidate)
    return result


def main():
    control=Control()
    state=control.get('control')
    if state['enabled'] or state['pilot_job_ids']:
        raise RuntimeError('Pause all queue execution before deploying legacy code')
    with control.db() as cursor:
        cursor.execute("SELECT job_id FROM backfill_jobs WHERE source_key LIKE 'legacy:%' AND status='running' AND lease_until>=UNIX_TIMESTAMP() LIMIT 1")
        if cursor.fetchone():raise RuntimeError('Drain the running historical invocation before deploying')
    config_path=ROOT/'config/constellation-infrastructure.json'
    config=json.loads(config_path.read_text())
    routes=json.loads((ROOT/'config/constellation-legacy-routes.json').read_text())['routes']
    session=boto3.Session(region_name=config['region']);s3=session.client('s3')
    source=s3.get_object(Bucket=config['bucket'],Key='research-data/operations/s3-runtime/current.json')
    try:seed=source['Body'].read()
    finally:source['Body'].close()
    sha=hashlib.sha256(seed).hexdigest()
    seed_key=config['prefix']+'/migration/seeds/'+sha+'.json'
    s3.put_object(Bucket=config['bucket'],Key=seed_key,Body=seed,ServerSideEncryption='AES256',ContentType='application/json')
    config.update(legacy_runtime_enabled=True,legacy_seed_key=seed_key,legacy_source_secret_arns=config.get('legacy_source_secret_arns',[]))
    config_path.write_text(json.dumps(config,indent=2)+'\n')
    files=dependencies([r['argv'][0] for r in routes])
    extras=[p for folder in ('config','schemas','runtime_source_files') for p in (ROOT/folder).rglob('*')
        if p.suffix in {'.json','.pem','.crt','.sql','.py','.sh'} and p.is_file()]
    extras += list(ROOT.glob('*.sql'))
    lock=subprocess.check_output([str(ROOT/'.venv-athena/bin/pip'),'freeze'],text=True)
    (ROOT/'constellation/migration/legacy-requirements.lock.txt').write_text(lock)
    bundle=ROOT/'constellation/migration/legacy-deploy.tar.gz'
    with tarfile.open(bundle,'w:gz') as archive:
        def add(name,body,mode=0o644):
            data=body.encode() if isinstance(body,str) else body
            info=tarfile.TarInfo(name);info.size=len(data);info.mode=mode;archive.addfile(info,io.BytesIO(data))
        for name,body in files.items():add('source/'+name,body)
        for path in extras:
            if path.name=='constellation-infrastructure.json':continue
            add('source/'+str(path.relative_to(ROOT)),path.read_bytes())
        worker_config={k:v for k,v in config.items() if k!='controller_secret_arn'}
        add('source/config/constellation-infrastructure.json',json.dumps(worker_config,indent=2))
        add('config/constellation-infrastructure.json',json.dumps(worker_config,indent=2))
        for name in ('__init__.py','control.py','shared_limits.py','legacy_routes.py','legacy_worker.py','worker.py','sources.py'):
            body=(ROOT/'constellation'/name).read_text()
            add('constellation/'+name,body)
            if name in ('__init__.py','control.py','shared_limits.py','legacy_routes.py','sources.py'):
                add('source/constellation/'+name,body)
        add('config/constellation-legacy-routes.json',(ROOT/'config/constellation-legacy-routes.json').read_bytes())
        add('legacy-requirements.lock.txt',lock)
        for name in ('constellation-legacy-worker.service','constellation-legacy-worker@.service','constellation-legacy-runtime-init.service','constellation-workers.slice'):
            add('constellation/'+name,(ROOT/'constellation'/name).read_bytes())
    digest=hashlib.sha256(bundle.read_bytes()).hexdigest();key=config['prefix']+'/deployments/legacy-'+digest+'.tar.gz'
    s3.upload_file(str(bundle),config['bucket'],key,ExtraArgs={'ServerSideEncryption':'AES256'})
    script='''set -eu
cd /opt/constellation
systemctl stop constellation-legacy-worker.service 'constellation-legacy-worker@*.service'
aws s3 cp BUNDLE tmp/legacy-deploy.tar.gz --region us-east-1 --only-show-errors
echo 'DIGEST  tmp/legacy-deploy.tar.gz' | sha256sum --check --status
tar -xzf tmp/legacy-deploy.tar.gz --no-same-owner
python3.12 -m venv legacy-venv
legacy-venv/bin/pip install --disable-pip-version-check -r legacy-requirements.lock.txt > tmp/legacy-pip.log 2>&1
python3.12 - <<'PREPARE'
import json,shutil,os
from pathlib import Path
base=Path('/opt/constellation')
routes=json.loads((base/'config/constellation-legacy-routes.json').read_text())['routes']
for row in routes:
 root=base/'legacy'/row['unit'];root.mkdir(parents=True,exist_ok=True)
 ram=Path('/dev/shm/constellation-legacy')/row['unit'];(ram/'locks').mkdir(parents=True,exist_ok=True)
 for path in (base/'source').rglob('*'):
  if not path.is_file():continue
  target=root/path.relative_to(base/'source');target.parent.mkdir(parents=True,exist_ok=True)
  rewrite=path.suffix in ('.py','.json','.sql','.sh')
  body=path.read_text() if rewrite else None
  if path.suffix=='.py' or (rewrite and '/home/ec2-user/data-collection-processing' in body):
   if target.exists():target.unlink()
   target.write_text(body.replace('/home/ec2-user/data-collection-processing',str(root)))
  else:
   # Immutable configuration/data files can share inodes across workspaces.
   # Python modules stay physical copies so __file__ resolves to each unit root.
   if target.exists():target.unlink()
   os.link(path,target)
 link=root/'.venv'
 if not link.exists():link.symlink_to(base/'legacy-venv',target_is_directory=True)
 for name in ('reports','mlperf-evidence-cache','ted-package-cache','collection-output'):
  link=root/name
  if not link.is_symlink():link.symlink_to(ram/'work'/name,target_is_directory=True)
PREPARE
mkdir -p /dev/shm/constellation-legacy
chown -R ec2-user:ec2-user /opt/constellation/legacy /opt/constellation/legacy-venv /opt/constellation/source /dev/shm/constellation-legacy
chown ec2-user:ec2-user config/constellation-infrastructure.json config/constellation-legacy-routes.json
install -m 0644 constellation/constellation-legacy-worker.service constellation/constellation-legacy-worker@.service constellation/constellation-legacy-runtime-init.service constellation/constellation-workers.slice /etc/systemd/system/
systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/constellation-legacy-worker.service
systemctl start constellation-legacy-runtime-init.service
systemctl disable constellation-legacy-worker.service
systemctl enable --now constellation-backfill@{1..5}.service constellation-legacy-worker@{1..4}.service
du -sh /opt/constellation/legacy /opt/constellation/legacy-venv
echo legacy_runtime_staged_collection_paused
'''.replace('BUNDLE',shlex.quote('s3://'+config['bucket']+'/'+key)).replace('DIGEST',digest)
    result=session.client('ssm').send_command(InstanceIds=[config['worker_instance_id']],DocumentName='AWS-RunShellScript',
        Parameters={'commands':[script]},TimeoutSeconds=1200)
    receipt={'command_id':result['Command']['CommandId'],'sha256':digest,'seed_sha256':sha,
        'seed_key':seed_key,'source_modules':len(files),'historical_routes':len(routes)-1,'collection_enabled':False}
    (ROOT/'constellation/migration/deployment.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':main()
