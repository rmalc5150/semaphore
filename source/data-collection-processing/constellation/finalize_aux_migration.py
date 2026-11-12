"""Enable shared lifecycle and recover failed capture lanes sequentially."""
from constellation.finish_aux_migration import remote,T3,M7

def main():
 remote(T3,"""from pathlib import Path
import subprocess
folder=Path('/etc/systemd/system/optima-metadata-controller.service.d');folder.mkdir(exist_ok=True)
(folder/'zzzzzz-m7-lifecycle.conf').write_text('[Service]\\nExecStart=\\nExecStart=/home/ec2-user/data-collection-processing/.venv-athena/bin/python -B -m constellation.m7_lifecycle metadata\\nTimeoutStartSec=15min\\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','start','optima-m7-shared-autostop.service'],check=True)
subprocess.run(['systemctl','enable','--now','optima-m7-shared-autostop.timer'],check=True)
for unit in ('optima-collection-daily.service','optima-eodhd-inventory.service','optima-nist-robotics-matching.service'):
 state=subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','--value'],text=True).strip()
 if state in ('failed','inactive'):
  subprocess.run(['systemctl','reset-failed',unit])
  subprocess.run(['systemctl','start','--no-block',unit],check=True)
print(subprocess.check_output(['systemctl','list-units','optima-*.service','--state=failed,activating','--no-pager'],text=True))
print(subprocess.check_output(['free','-m'],text=True))
""")
 remote(M7,"""import subprocess
print(subprocess.check_output(['systemctl','list-units','--all','optima-m7-*','optima-*metadata*','--no-pager'],text=True))
print(subprocess.check_output(['journalctl','--since','10 minutes ago','-u','optima-m7-aux-specialist-publication.service','-u','optima-m7-aux-news-publication.service','-u','optima-m7-aux-crossref-publication-resumed.service','-n','35','--no-pager'],text=True))
""")
if __name__=='__main__':main()
