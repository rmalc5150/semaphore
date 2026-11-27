import json,subprocess
from pathlib import Path
root=Path('/home/ec2-user/data-collection-processing');out=root/'repair-notes/2026-11-24-service-checkup';unitroot=Path('/etc/systemd/system')
units=[line.split()[0]for line in subprocess.check_output(['systemctl','list-unit-files','--type=service','--no-legend','--no-pager','optima-*','ec2-code-backup.service','constellation-research-daily@.service'],text=True).splitlines()if line.split()]
changed=[]
body='[Unit]\n# Recheck before namespace setup even when the boot initializer is still active.\nRequires=optima-s3-runtime-ensure.service\nAfter=optima-s3-runtime-ensure.service\n'
for unit in units:
 props=subprocess.check_output(['systemctl','show',unit.replace('@.service','@runtime-check.service'),'-p','ReadWritePaths','--value'],text=True).strip().split()
 if '/dev/shm/optima-s3'not in props:continue
 folder=unitroot/(unit+'.d');folder.mkdir(exist_ok=True)
 path=folder/'zzzzzzzzzzz-runtime-ensure.conf'
 if path.exists():(out/(unit+'-ensure-before.conf')).write_text(path.read_text())
 path.write_text(body);repo=root/'systemd/s3-runtime'/(unit+'.d');repo.mkdir(parents=True,exist_ok=True);(repo/path.name).write_text(body);changed.append(unit)
(out/'workspace-guard-units.json').write_text(json.dumps(changed,indent=2));print(json.dumps({'guarded_units':len(changed)}))
