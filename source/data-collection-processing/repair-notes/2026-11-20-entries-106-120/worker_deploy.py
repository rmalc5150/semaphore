"""Dispatcher for the staged worker repair bundle."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

import boto3

B = 'data-collection-059416028963-us-east-1-an'
BASE = 'research-data/constellation-backfill/repairs/entries-106-120-20261120/'
AUX = Path('/opt/constellation/auxiliary-publication/source')
OVERLAY = Path('/opt/constellation/tmp/review-106-120')
BASE_DIR = Path('/opt/constellation')
s3 = boto3.client('s3',region_name='us-east-1')


def read(key):
    with s3.get_object(Bucket=B,Key=BASE+key)['Body'] as stream:
        return stream.read()


def atomic(path, body):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        old=path.read_bytes()
        if old != body and not str(path).startswith(str(OVERLAY)):
            backup=BASE_DIR/'tmp/review-106-120-backup'/hashlib.sha256(str(path).encode()).hexdigest()[:16]/path.name
            backup.parent.mkdir(parents=True,exist_ok=True)
            if not backup.exists():
                backup.write_bytes(old)
    tmp=path.with_name(path.name+'.review-20261120')
    tmp.write_bytes(body)
    os.chown(tmp,1000,1000)
    os.chmod(tmp,0o644)
    tmp.replace(path)


def save_json(path, value):
    atomic(path,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())


def start(script, unit, root):
    subprocess.run([
        'systemd-run','--no-block','--collect','--unit='+unit,
        '-p','User=ec2-user','-p','WorkingDirectory='+str(root),
        '-p','Slice=constellation-workers.slice','-p','MemoryMax=1792M',
        '-p','CPUQuota=150%','-p','RuntimeMaxSec=25min',
        '-p','Environment=CONSTELLATION_ROLE=worker CONSTELLATION_SHARED_HTTP_LIMITS=1 AWS_DEFAULT_REGION=us-east-1',
        '/opt/constellation/legacy-venv/bin/python','-B',str(root/script)
    ],check=True)


def bundle():
    plan=json.loads(read('deployment-plan.json'))
    blob=read(plan['package'])
    assert hashlib.sha256(blob).hexdigest()==plan['package_sha256']
    with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as archive:
        data={}
        for name,expected in plan['files'].items():
            body=archive.extractfile(name).read()
            assert hashlib.sha256(body).hexdigest()==expected,name
            if name.endswith('.py'):
                compile(body,name,'exec')
            data[name]=body
    return data


def prepare():
    if (BASE_DIR/'batch-paused').exists():
        raise RuntimeError('worker_batch_is_paused')
    files=bundle()
    # Isolated proof directory. Runtime dependencies are linked read-only.
    for parent in ('','config','metadata_engine','constellation'):
        root=OVERLAY/parent
        root.mkdir(parents=True,exist_ok=True)
        for src in (AUX/parent).iterdir():
            if parent=='' and src.name in ('config','metadata_engine','constellation'):
                continue
            if src.is_file() or src.name=='schemas':
                target=root/src.name
                if not target.exists() and not target.is_symlink():
                    target.symlink_to(src)
    for name,body in files.items():
        atomic(OVERLAY/name,body)
    start('worker_proof.py','optima-review-106-120-raw',OVERLAY)


def install():
    scope=json.loads(read('activation-scope.json'))
    eligible=set(scope['sources'])
    updates=json.loads(read('capture-updates.json'))
    policies=json.loads(read('policies.json'))
    jobs=json.loads(read('daily-worker-map.json'))
    daily={name:source for name,source in jobs.items() if source in eligible}
    files=bundle()
    roots=[BASE_DIR/'metadata-engine-runtime', AUX, BASE_DIR/'source']
    roots.extend(BASE_DIR/'legacy'/('constellation-public-'+s+'.service') for s in eligible if s in updates)
    for root in roots:
        if not root.is_dir():
            raise RuntimeError('missing_runtime '+str(root))
        for name,body in files.items():
            if name in ('worker_proof.py','worker_publish.py') and root!=AUX:
                continue
            atomic(root/name,body)
        p=root/'config/constellation-public-sources.json'
        if p.exists():
            document=json.loads(p.read_text())
            document['sources']=[{**row,**updates[row['source']]} if row['source'] in eligible and row['source'] in updates else row for row in document['sources']]
            save_json(p,document)
        p=root/'config/metadata-engine.json'
        if p.exists():
            document=json.loads(p.read_text())
            document['contracts'].update({source:policies[source] for source in eligible})
            document.setdefault('verified_source_failure_handling',{}).update({source:'queue_by_source_date' for source in eligible})
            document['build_sha256']=hashlib.sha256(b''.join(q.read_bytes() for q in sorted((root/'metadata_engine').glob('*.py')))).hexdigest()
            save_json(p,document)
    path=AUX/'config/m7-public-file-jobs.json'
    previous=json.loads(path.read_text()) if path.exists() else {}
    save_json(path,{**previous,**daily})
    system=Path('/etc/systemd/system')
    template=(system/'optima-m7-capture-public-ndb-daily.service').read_text()
    units=[]
    for name in daily:
        unit='optima-m7-capture-'+name+'.service'
        p=system/unit
        text=template.replace('public-ndb-daily',name)
        p.write_text(text)
        directory=BASE_DIR/'tmp/publication-staging'/unit
        directory.mkdir(parents=True,exist_ok=True)
        os.chown(directory,1000,1000)
        units.append(unit)
    if units:
        subprocess.run(['systemctl','daemon-reload'],check=True)
        subprocess.run(['systemd-analyze','verify',*units],check=True)
    print(json.dumps({'worker_roots':[str(root) for root in roots],'daily_units':units}))


def publish():
    start('worker_publish.py','optima-review-106-120-publication',AUX)


if __name__=='__main__':
    import sys
    {'prepare':prepare,'install':install,'publish':publish}[sys.argv[1]]()
