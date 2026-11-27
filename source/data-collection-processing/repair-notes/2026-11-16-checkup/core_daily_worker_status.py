import subprocess,json
for unit in ['optima-m7-aux-collection-daily.service','optima-checkup-1116-coverage-publication.service','optima-checkup-1116-second.service']:
 print(unit,subprocess.run(['systemctl','show',unit,'-p','ActiveState','-p','Result','-p','MemoryCurrent'],capture_output=True,text=True).stdout)
 if 'collection-daily'in unit:print(subprocess.run(['systemctl','cat',unit],capture_output=True,text=True).stdout[:2000])
from pathlib import Path
p=Path('/opt/constellation/tmp/checkup1116/second.log');rows=[]
for line in p.read_text().splitlines():
 try:rows.append(json.loads(line))
 except Exception:pass
from collections import Counter
print('SECOND',json.dumps({'steps':len(rows),'counts':dict(Counter(r.get('status')for r in rows)),'last':[{k:r.get(k)for k in('source','start','status','reason')}for r in rows[-2:]]}))
