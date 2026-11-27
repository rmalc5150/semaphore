import subprocess,json
from pathlib import Path
units=['optima-m7-capture-assignments-reviewed-historical.service','optima-m7-aux-cms-catalog-publication.service','optima-m7-capture-patents-daily.service','constellation-workers.slice']
print(subprocess.run(['systemctl','--failed','--no-pager'],capture_output=True,text=True).stdout)
for unit in units:
 print(subprocess.run(['systemctl','show',unit,'-p','Id','-p','ActiveState','-p','Result','-p','MemoryCurrent','-p','MemoryMax','-p','ExecMainStatus'],capture_output=True,text=True).stdout)
 if unit.endswith('service'):print(subprocess.run(['journalctl','-u',unit,'--since','2026-11-15','-n','8','--no-pager'],capture_output=True,text=True).stdout[-4000:])
print(subprocess.run(['df','-h','/opt/constellation'],capture_output=True,text=True).stdout)
print('SOURCE_ROOTS',[str(p)for p in Path('/opt/constellation').glob('*/source')])
