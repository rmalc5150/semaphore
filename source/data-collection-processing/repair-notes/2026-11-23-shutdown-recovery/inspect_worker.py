import os,sys,json,subprocess
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
print('BOOTS',subprocess.run(['journalctl','--list-boots','--no-pager'],capture_output=True,text=True).stdout[-1200:])
print('FAILED',subprocess.run(['systemctl','--failed','--no-pager'],capture_output=True,text=True).stdout[-2500:])
for u in ['optima-m7-capture-assignments-reviewed-historical.service','optima-m7-aux-collection-daily.service','optima-m7-capture-patents-daily.service','optima-m7-research-publication.service']:
 print('UNIT',u,subprocess.run(['systemctl','show',u,'-p','ActiveState','-p','Result','-p','ExecMainStatus','-p','ExecMainExitTimestamp'],capture_output=True,text=True).stdout.replace('\n',' '))
 print(subprocess.run(['journalctl','-u',u,'-n','4','--no-pager','-o','cat'],capture_output=True,text=True).stdout[-1800:])
print('METADATA',subprocess.run(['systemctl','list-units','--all','--no-pager','--plain','optima-metadata*','constellation-*worker*','constellation-backfill@*'],capture_output=True,text=True).stdout[-5000:])
