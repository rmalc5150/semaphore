"""Run three source-fenced, bounded metadata workers on the resized M7."""
from constellation.finish_aux_migration import remote,M7

def main():
 remote(M7,'''from pathlib import Path
import subprocess
base=Path('/etc/systemd/system')
unit=(base/'optima-metadata-worker.service').read_text()
unit=unit.replace('Description=Validate and label committed raw data on m7i','Description=Additional source-fenced metadata worker on m7')
unit=unit.replace('--max-seconds 210','--max-seconds 210')
timer='[Unit]\\nDescription=Continue additional metadata worker\\n[Timer]\\nOnBootSec=20s\\nOnUnitInactiveSec=15s\\n[Install]\\nWantedBy=timers.target\\n'
for name in ('optima-metadata-worker-extra','optima-metadata-worker-extra2','optima-metadata-worker-extra3'):
 (base/(name+'.service')).write_text(unit)
 (base/(name+'.timer')).write_text(timer)
 folder=base/(name+'.service.d');folder.mkdir(exist_ok=True)
 (folder/'80-efficient-metadata-batches.conf').write_text('[Service]\\nExecStart=\\nExecStart=/opt/constellation/legacy-venv/bin/python -B -m metadata_engine.worker --max-jobs 64 --max-seconds 210\\nCPUWeight=200\\n')
 (folder/'zzzz-capacity.conf').write_text('[Service]\\nSlice=constellation-workers.slice\\nCPUQuota=200%\\nCPUWeight=150\\nMemoryHigh=1536M\\nMemoryMax=2G\\nMemorySwapMax=0\\n')
primary=base/'optima-metadata-worker.service.d';primary.mkdir(exist_ok=True)
(primary/'80-efficient-metadata-batches.conf').write_text('[Service]\\nExecStart=\\nExecStart=/opt/constellation/legacy-venv/bin/python -B -m metadata_engine.worker --max-jobs 64 --max-seconds 210\\nCPUWeight=200\\n')
(primary/'zzzz-capacity.conf').write_text('[Service]\\nSlice=constellation-workers.slice\\nCPUQuota=200%\\nCPUWeight=150\\nMemoryHigh=1536M\\nMemoryMax=2G\\nMemorySwapMax=0\\n')
folder=base/'optima-metadata-worker.timer.d';folder.mkdir(exist_ok=True)
(folder/'50-throughput.conf').write_text('[Timer]\\nOnUnitInactiveSec=\\nOnUnitInactiveSec=15s\\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemd-analyze','verify',*[str(base/(name+suffix)) for name in ('optima-metadata-worker-extra','optima-metadata-worker-extra2','optima-metadata-worker-extra3') for suffix in ('.service','.timer')]],check=True)
subprocess.run(['systemctl','enable','--now','optima-metadata-worker-extra.timer','optima-metadata-worker-extra2.timer','optima-metadata-worker-extra3.timer'],check=True)
subprocess.run(['systemctl','restart','optima-metadata-worker.timer'],check=True)
subprocess.run(['systemctl','start','--no-block','optima-metadata-worker-extra.service'],check=True)
subprocess.run(['systemctl','start','--no-block','optima-metadata-worker-extra2.service'],check=True)
subprocess.run(['systemctl','start','--no-block','optima-metadata-worker-extra3.service'],check=True)
print(subprocess.check_output(['systemctl','show','optima-metadata-worker.service','optima-metadata-worker-extra.service','optima-metadata-worker-extra2.service','optima-metadata-worker-extra3.service','-p','Id','-p','ActiveState','-p','Result','-p','MemoryMax','-p','CPUQuotaPerSecUSec'],text=True))
print(subprocess.check_output(['systemctl','list-timers','optima-metadata-worker*.timer','--no-pager'],text=True))
''')
if __name__=='__main__':main()
