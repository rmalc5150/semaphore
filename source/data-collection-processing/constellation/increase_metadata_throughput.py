"""Add one source-fenced metadata worker within measured m7 capacity."""
from constellation.finish_aux_migration import remote,M7

def main():
 remote(M7,'''from pathlib import Path
import subprocess
base=Path('/etc/systemd/system')
unit=(base/'optima-metadata-worker.service').read_text()
unit=unit.replace('Description=Validate and label committed raw data on m7i','Description=Additional source-fenced metadata worker on m7')
unit=unit.replace('--max-seconds 210','--max-seconds 210')
(base/'optima-metadata-worker-extra.service').write_text(unit)
timer='[Unit]\\nDescription=Continue additional metadata worker\\n[Timer]\\nOnBootSec=20s\\nOnUnitInactiveSec=15s\\n[Install]\\nWantedBy=timers.target\\n'
(base/'optima-metadata-worker-extra.timer').write_text(timer)
folder=base/'optima-metadata-worker.timer.d';folder.mkdir(exist_ok=True)
(folder/'50-throughput.conf').write_text('[Timer]\\nOnUnitInactiveSec=\\nOnUnitInactiveSec=15s\\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemd-analyze','verify',str(base/'optima-metadata-worker-extra.service'),str(base/'optima-metadata-worker-extra.timer')],check=True)
subprocess.run(['systemctl','enable','--now','optima-metadata-worker-extra.timer'],check=True)
subprocess.run(['systemctl','restart','optima-metadata-worker.timer'],check=True)
subprocess.run(['systemctl','start','--no-block','optima-metadata-worker-extra.service'],check=True)
print(subprocess.check_output(['systemctl','show','optima-metadata-worker-extra.service','-p','ActiveState','-p','Result','-p','MemoryMax','-p','CPUQuotaPerSecUSec'],text=True))
print(subprocess.check_output(['systemctl','list-timers','optima-metadata-worker*.timer','--no-pager'],text=True))
''')
if __name__=='__main__':main()
