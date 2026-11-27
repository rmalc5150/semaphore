import subprocess,json
from pathlib import Path
print(subprocess.run(['systemctl','show','optima-checkup-1116-replays.service','-p','ActiveState','-p','Result','-p','ExecMainStatus'],capture_output=True,text=True).stdout)
p=Path('/opt/constellation/tmp/checkup1116/replay.log');rows=[]
for line in p.read_text().splitlines()if p.exists()else[]:
 try:rows.append(json.loads(line))
 except Exception:pass
from collections import Counter
print('REPLAYS',json.dumps({'steps':len(rows),'counts':dict(Counter(r.get('status')for r in rows)),'last':[{k:r.get(k)for k in('source','start','status','reason','records')}for r in rows[-5:]]}))
print('SUMMARY',subprocess.run(['journalctl','-u','optima-m7-summary-worker.service','-n','4','--no-pager'],capture_output=True,text=True).stdout[-1200:])
print('CAPTURE_UNITS',subprocess.run(['systemctl','list-units','optima-m7-capture*','--all','--no-pager','--plain'],capture_output=True,text=True).stdout[-3500:])
