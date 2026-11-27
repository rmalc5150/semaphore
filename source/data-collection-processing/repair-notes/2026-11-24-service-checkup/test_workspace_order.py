"""Live ordering regression using an isolated, empty canary path only."""
import json,subprocess
from pathlib import Path
root=Path('/home/ec2-user/data-collection-processing');base=Path('/dev/shm/optima-runtime-order-regression-20261124');unit='optima-runtime-order-regression-ensure-20261124.service';path=Path('/etc/systemd/system')/unit
assert not base.exists(), 'Canary path already exists; refuse to alter it'
path.write_text('[Service]\nType=oneshot\nUser=ec2-user\nExecStart=/usr/bin/mkdir -p '+str(base/'locks')+'\n');subprocess.run(['systemctl','daemon-reload'],check=True)
results=[]
for number in (1,2):
 assert not base.exists()
 args=['systemd-run','--unit=optima-runtime-order-regression-'+str(number)+'-20261124','--wait','--pipe','--property=Type=oneshot','--property=User=ec2-user','--property=Requires='+unit,'--property=After='+unit,'--property=ProtectSystem=strict','--property=ReadOnlyPaths=/dev/shm','--property=ReadWritePaths='+str(base),'/usr/bin/test','-d',str(base/'locks')]
 r=subprocess.run(args,capture_output=True,text=True);results.append({'cycle':number,'initially_missing':True,'exit':r.returncode,'created':base.is_dir()});assert r.returncode==0,r.stderr
 (base/'locks').rmdir();base.rmdir()  # Only this test's empty directories.
(root/'repair-notes/2026-11-24-service-checkup/workspace-regression.json').write_text(json.dumps(results,indent=2));print(json.dumps(results));path.unlink();subprocess.run(['systemctl','daemon-reload'],check=True)
