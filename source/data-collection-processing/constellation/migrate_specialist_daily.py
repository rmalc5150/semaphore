"""Remove heavy specialist planning from the controller's shared RAM workspace."""
import base64
from constellation.finish_aux_migration import remote,M7,T3,ROOT

def main():
 for name in ('specialist_inputs.py','specialist_discovery_queue.py','m7_specialist_daily.py'):
  payload=base64.b64encode((ROOT/name).read_bytes()).decode()
  remote(M7,'''from pathlib import Path
import base64,os
p=Path('/opt/constellation/auxiliary-publication/source')/__NAME__;tmp=p.with_suffix('.specialist-migration');tmp.write_bytes(base64.b64decode(__PAYLOAD__));os.chown(tmp,1000,1000);tmp.replace(p)
print('Staged',p.name)
'''.replace('__NAME__',repr(name)).replace('__PAYLOAD__',repr(payload)))
 remote(M7,'''from pathlib import Path
import subprocess
root='/opt/constellation/auxiliary-publication/source'
unit='[Unit]\\nDescription=Bounded specialist daily planning and capture on m7\\nAfter=network-online.target\\n[Service]\\nType=oneshot\\nUser=ec2-user\\nWorkingDirectory='+root+'\\nExecStart=/opt/constellation/legacy-venv/bin/python -B m7_specialist_daily.py\\nSlice=constellation-workers.slice\\nMemoryHigh=1G\\nMemoryMax=1536M\\nMemorySwapMax=0\\nCPUQuota=100%\\nTimeoutStartSec=30min\\nTimeoutStopSec=120\\nKillSignal=SIGINT\\nSuccessExitStatus=2\\nEnvironment=AWS_DEFAULT_REGION=us-east-1\\nEnvironment=CONSTELLATION_ROLE=worker\\nEnvironment=CONSTELLATION_SHARED_HTTP_LIMITS=1\\nEnvironment=METADATA_ENGINE_NOTIFY=1\\n'
Path('/etc/systemd/system/optima-m7-specialist-daily.service').write_text(unit);subprocess.run(['systemctl','daemon-reload'],check=True)
print('m7 specialist daily unit installed')
''')
 remote(T3,'''from pathlib import Path
import subprocess
subprocess.run(['systemctl','stop','optima-specialist-daily.service'],check=True)
folder=Path('/etc/systemd/system/optima-specialist-daily.service.d');folder.mkdir(exist_ok=True)
(folder/'zzzzzzzz-m7-processing.conf').write_text('[Service]\\nExecStart=\\nExecStart=/home/ec2-user/data-collection-processing/.venv-athena/bin/python -B -m constellation.m7_lifecycle dispatch --unit optima-m7-specialist-daily.service\\nSlice=system.slice\\nMemoryHigh=128M\\nMemoryMax=256M\\nCPUQuota=50%\\nTimeoutStartSec=10min\\nReadWritePaths=/home/ec2-user/data-collection-processing/constellation/autostop\\n')
timer=Path('/etc/systemd/system/optima-specialist-daily.timer.d');timer.mkdir(exist_ok=True)
(timer/'60-bounded-m7-passes.conf').write_text('[Timer]\\nOnCalendar=\\nOnBootSec=2min\\nOnUnitInactiveSec=2min\\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','restart','optima-specialist-daily.timer'],check=True)
subprocess.run(['systemctl','start','--no-block','optima-specialist-daily.service'],check=True)
print('Controller now dispatches bounded m7 specialist passes; old RAM lock released')
''')

if __name__=='__main__':main()
