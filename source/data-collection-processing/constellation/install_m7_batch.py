"""Install tested catch-up/batch lifecycle without interrupting current work."""
import base64
import io
import tarfile

from constellation.finish_aux_migration import M7, T3, ROOT, remote


def main():
    # Gate new worker starts first. No marker is installed during catch-up.
    remote(M7, """from pathlib import Path
import subprocess
base=Path('/etc/systemd/system')
folders=['optima-.service.d','constellation-backfill@.service.d','constellation-legacy-worker@.service.d','constellation-public-worker@.service.d']
for name in folders:
    folder=base/name;folder.mkdir(exist_ok=True)
    (folder/'95-m7-batch-gate.conf').write_text('[Unit]\\nConditionPathExists=!/opt/constellation/batch-paused\\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemd-analyze','verify','optima-metadata-worker.service','optima-metadata-worker-extra7.service'],check=True)
print(subprocess.check_output(['systemctl','show','optima-metadata-worker.service','-p','Conditions'],text=True))
""")
    files = ['constellation/m7_lifecycle.py', 'constellation/m7_batch.py', 'config/m7-batch-policy.json', 'test_m7_batch.py', 'constellation/autostop/BATCH_POLICY.md']
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        for name in files:
            archive.add(ROOT / name, arcname=name)
    payload = base64.b64encode(buffer.getvalue()).decode()
    remote(T3, """import base64,fcntl,io,json,os,subprocess,tarfile,time
from pathlib import Path
root=Path.cwd();lock=(root/'constellation/autostop/m7-lifecycle.lock').open('a')
with lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    backup=root/'constellation/autostop'/('batch-install-backup-'+str(int(time.time())))
    backup.mkdir()
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(PAYLOAD)),mode='r:gz') as archive:
        for member in archive.getmembers():
            path=root/member.name
            if path.exists():
                prior=backup/member.name;prior.parent.mkdir(parents=True,exist_ok=True);prior.write_bytes(path.read_bytes())
            data=archive.extractfile(member).read()
            if member.name.endswith('.py'):compile(data,str(path),'exec')
            temporary=path.with_suffix(path.suffix+'.batch-new');temporary.write_bytes(data);os.chown(temporary,1000,1000);temporary.replace(path)
    subprocess.run([str(root/'.venv-athena/bin/python'),'-B','-m','unittest','test_m7_batch'],check=True)
    config=Path('/etc/systemd/system/optima-m7-shared-autostop.service.d/90-batch.conf')
    config.parent.mkdir(exist_ok=True)
    config.write_text('[Service]\\nTimeoutStartSec=10min\\n')
    subprocess.run(['systemctl','daemon-reload'],check=True)
    from constellation.m7_batch import read,save
    state=read();save(state)
    print(json.dumps({'phase':state['phase'],'backup':str(backup)}))
# The batch lifecycle supersedes the historical-only EC2 stop path, which
# does not account for the shared metadata and publication work.
subprocess.run(['systemctl','disable','--now','constellation-historical-autostop.timer'],check=True)
subprocess.run(['systemctl','enable','--now','optima-m7-shared-autostop.timer'],check=True)
subprocess.run(['systemctl','start','--no-block','optima-m7-shared-autostop.service'],check=True)
""".replace('PAYLOAD', repr(payload)))


if __name__ == '__main__':
    main()
