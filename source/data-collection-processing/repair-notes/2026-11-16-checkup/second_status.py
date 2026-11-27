import json,subprocess
from pathlib import Path
p=Path('/opt/constellation/tmp/checkup1116/second.log')
print(subprocess.run(['systemctl','show','optima-checkup-1116-second.service','-p','ActiveState','-p','Result','-p','ExecMainStatus'],capture_output=True,text=True).stdout)
rows=[]
for line in p.read_text().splitlines()if p.exists()else[]:
 try:rows.append(json.loads(line))
 except Exception:pass
from collections import Counter
print(json.dumps({'steps':len(rows),'counts':dict(Counter(r.get('status')for r in rows)),'latest':[{k:r.get(k)for k in('source','start','status','reason','records')}for r in rows[-5:]]}))
