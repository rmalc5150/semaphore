import subprocess,json
from pathlib import Path
units=['constellation-backfill@'+str(i)+'.service'for i in range(1,6)]+['constellation-legacy-worker@'+str(i)+'.service'for i in range(1,7)]+['constellation-public-worker@'+str(i)+'.service'for i in range(1,5)]
print('EXECUTORS',sum(subprocess.run(['systemctl','is-active','--quiet',u]).returncode==0 for u in units),len(units))
for u in ['optima-fda-gap-repair-20261116b.service','optima-fda-repair-publication-20261116.service','optima-metadata-streaming.timer','optima-m7-summary-worker.service']:
 print(u,subprocess.run(['systemctl','show',u,'-p','ActiveState','-p','Result'],capture_output=True,text=True).stdout.replace('\n',' '))
p=Path('/opt/constellation/tmp/checkup1116-afternoon/fda-publication.log');print('FDA_PUBLICATION',p.read_text()[-1800:] if p.exists()else'none')
