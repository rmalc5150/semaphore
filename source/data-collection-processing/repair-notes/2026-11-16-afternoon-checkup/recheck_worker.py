import subprocess,json
from pathlib import Path
for unit in ['optima-m7-capture-patents-prosecution.service','optima-m7-capture-patents-daily.service','optima-fda-gap-repair-20261116b.service','optima-fda-repair-publication-20261116.service']:
 print('UNIT',unit,subprocess.run(['systemctl','show',unit,'-p','ActiveState','-p','Result'],capture_output=True,text=True).stdout.replace('\n',' '))
 if 'patents' in unit:print(subprocess.run(['journalctl','-u',unit,'-n','5','--no-pager','-o','cat'],capture_output=True,text=True).stdout[-3500:])
for n in ['fda-continuation.log','fda-publication.log']:
 p=Path('/opt/constellation/tmp/checkup1116-afternoon')/n
 print(n,p.read_text()[-2200:]if p.exists()else'none')
