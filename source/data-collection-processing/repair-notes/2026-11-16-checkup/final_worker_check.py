import subprocess,json
from pathlib import Path
print('FAILED_UNITS',subprocess.run(['systemctl','--failed','--no-pager','--plain'],capture_output=True,text=True).stdout)
print('METADATA',subprocess.run(['systemctl','list-units','*metadata*','*streaming*','constellation-backfill@*','--all','--no-pager','--plain'],capture_output=True,text=True).stdout[-4500:])
print('DAILY',subprocess.run(['journalctl','-u','optima-m7-aux-collection-daily.service','-n','5','--no-pager'],capture_output=True,text=True).stdout[-2200:])
for n in ['second','coverage-publication','all-publication']:
 print(n,subprocess.run(['systemctl','show','optima-checkup-1116-'+n+'.service','-p','ActiveState','-p','Result','-p','ExecMainStatus'],capture_output=True,text=True).stdout)
for name in ['all-publish.log','second.log']:
 p=Path('/opt/constellation/tmp/checkup1116')/name
 if p.exists():
  rows=[]
  for line in p.read_text().splitlines():
   try:rows.append(json.loads(line))
   except Exception:pass
  from collections import Counter
  print(name,json.dumps({'rows':len(rows),'counts':dict(Counter(r.get('status')for r in rows)),'last':rows[-1]if name!='second.log'and rows else({k:rows[-1].get(k)for k in ('source','start','status','reason')}if rows else None)}))
