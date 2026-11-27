import subprocess,json
from pathlib import Path
units=['optima-m7-capture-assignments-reviewed-historical.service','optima-m7-aux-cms-catalog-publication.service','optima-m7-aux-fda-product-codes-capture.service','optima-m7-aux-fda-reviewed-publication.service','optima-m7-capture-nist-robotics-daily.service','optima-m7-aux-patents-prosecution-publication.service','optima-m7-specialist-daily.service','optima-m7-aux-collection-daily.service']
for unit in units:
 print('UNIT',unit,subprocess.run(['systemctl','show',unit,'-p','ActiveState','-p','Result','-p','ExecMainStatus'],capture_output=True,text=True).stdout.replace('\n',' '))
 n='10'if unit.endswith('specialist-daily.service')else'3'
 print(subprocess.run(['journalctl','-u',unit,'-n',n,'--no-pager'],capture_output=True,text=True).stdout[-2800:])
