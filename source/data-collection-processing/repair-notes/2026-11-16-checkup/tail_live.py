import subprocess,json
from pathlib import Path
for unit in ['optima-m7-aux-collection-daily.service','optima-checkup-1116-coverage-publication.service','optima-checkup-1116-all-publication.service','optima-checkup-1116-second.service']:
 print(unit,subprocess.run(['systemctl','show',unit,'-p','ActiveState','-p','Result','-p','MemoryCurrent'],capture_output=True,text=True).stdout)
print('DAILY',subprocess.run(['journalctl','-u','optima-m7-aux-collection-daily.service','-n','3','--no-pager'],capture_output=True,text=True).stdout[-2200:])
for name in ['publish.log','all-publish.log','second.log']:
 p=Path('/opt/constellation/tmp/checkup1116')/name
 print(name,p.read_text()[-1700:]if p.exists()else'no log')
