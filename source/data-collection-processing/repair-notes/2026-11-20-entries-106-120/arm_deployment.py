"""Stage the checked files and enable a one-time continuation on normal m7 wake."""
import hashlib
import io
import json
import tarfile
from pathlib import Path
from ops import B, BASE, P, T3, remote, session

ROOT=P.resolve().parents[1]
files=[
    'trade_mining_sources.py','provider_tls.py','config/anm-intermediate.pem',
    'config/sernageomin-intermediate.pem','public_source_scope.py','public_source_capture.py','regional_source_review.py',
    'metadata_engine/census_trade.py','metadata_engine/trade_mining.py',
    'metadata_engine/evidence.py','metadata_engine/worker.py','metadata_engine/source_policies.py',
    'metadata_engine/controller.py','reviewed_metadata_publication.py','constellation/m7_capture_plan.py',
]
payload={name:(ROOT/name).read_bytes() for name in files}
payload.update({name:(P/name).read_bytes() for name in ('worker_proof.py','worker_publish.py')})
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w:gz') as archive:
    for name,body in payload.items():
        if name.endswith('.py'):
            compile(body,name,'exec')
        entry=tarfile.TarInfo(name)
        entry.size=len(body)
        archive.addfile(entry,io.BytesIO(body))
archive=buffer.getvalue()
digest=hashlib.sha256(archive).hexdigest()
package='deployment/'+digest+'.tar.gz'
plan={'files':{name:hashlib.sha256(body).hexdigest() for name,body in payload.items()},
      'package':package,'package_sha256':digest,
      'worker_deploy_sha256':hashlib.sha256((P/'worker_deploy.py').read_bytes()).hexdigest(),
      'activation':'after native daily and historical worker validation under normal lifecycle',
      'publication':'exact job IDs from successfully validated replacement inputs',
      'retained':'existing accepted legacy jobs, raw bytes, deliberate pauses and unrelated source settings'}
(P/'deployment-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
s3=session.client('s3')
s3.put_object(Bucket=B,Key=BASE+package,Body=archive,ServerSideEncryption='AES256')
for name in ('deployment-plan.json','worker_deploy.py','capture-updates.json','policies.json','daily-worker-map.json',
             'staged-raw-proof.json','census-proof.json','review-status.json','before.json','tests.log'):
    body=(P/name).read_bytes()
    digest=hashlib.sha256(body).hexdigest()
    s3.put_object(Bucket=B,Key=BASE+name,Body=body,Metadata={'sha256':digest},ServerSideEncryption='AES256')
    info=s3.head_object(Bucket=B,Key=BASE+name)
    assert info['ContentLength']==len(body) and info['Metadata']['sha256']==digest

script=r'''
from pathlib import Path
import json,os,subprocess,time
root=Path.cwd()
repair=root/'repair-notes/2026-11-20-entries-106-120'
for name in ('deploy_on_wake.py','worker_deploy.py','worker_proof.py','worker_publish.py','verify_live.py','update_review.py','ops.py'):
    compile((repair/name).read_bytes(),name,'exec')
service='optima-source-review-106-120'
system=Path('/etc/systemd/system')
service_text=f"""[Unit]
Description=Verify and activate source repairs 106-120 when m7 is available
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory={root}
Environment=PYTHONPATH={root}:{repair}
Environment=AWS_CONFIG_FILE=/dev/null
Environment=AWS_SHARED_CREDENTIALS_FILE=/dev/null
Environment=AWS_DEFAULT_REGION=us-east-1
Environment=CONSTELLATION_ROLE=controller
ExecStart={root}/.venv-athena/bin/python -B {repair}/deploy_on_wake.py
MemoryMax=384M
CPUQuota=50%
TimeoutStartSec=8min
"""
timer_text=f"""[Unit]
Description=Continue reviewed source repairs after normal m7 wake

[Timer]
OnActiveSec=1s
OnUnitInactiveSec=120s
Unit={service}.service
"""
(system/(service+'.service')).write_text(service_text)
(system/(service+'.timer')).write_text(timer_text)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemd-analyze','verify',service+'.service',service+'.timer'],check=True)
subprocess.run(['systemctl','start',service+'.timer'],check=True)
print(subprocess.check_output(['systemctl','show',service+'.timer','-p','ActiveState','-p','SubState'],text=True))
'''
print(remote(T3,script)['out'])
