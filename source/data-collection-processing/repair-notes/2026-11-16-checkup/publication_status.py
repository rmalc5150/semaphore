import subprocess,json
from pathlib import Path
print(subprocess.run(['systemctl','show','optima-checkup-1116-publication.service','-p','ActiveState','-p','Result','-p','ExecMainStatus'],capture_output=True,text=True).stdout)
p=Path('/opt/constellation/tmp/checkup1116/publish.log');print(p.read_text()[-4000:]if p.exists()else'no log')
