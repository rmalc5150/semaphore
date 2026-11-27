import subprocess,json,os
from pathlib import Path
for unit in ['optima-m7-specialist-daily.service','optima-m7-aux-collection-daily.service']:
 r=subprocess.run(['journalctl','-u',unit,'--since','2026-11-16 16:15:00','--until','2026-11-16 16:30:00','--no-pager','-o','cat'],capture_output=True,text=True)
 for line in r.stdout.splitlines():
  if any(s in line for s in ['AccessDenied','prerequisite_incomplete','dispatching']): print(unit,line[:10000])
print('FIND product codes',subprocess.run(['systemctl','list-units','--all','--no-pager','--plain'],capture_output=True,text=True).stdout.count('product'))
for line in subprocess.run(['systemctl','list-unit-files','--no-pager'],capture_output=True,text=True).stdout.splitlines():
 if 'product' in line and 'fda' in line:print(line)
for p in ['/opt/constellation/legacy/optima-news-collection.service','/opt/constellation/auxiliary-publication/source']:
 root=Path(p)
 for f in root.glob('config/*news*json'):
  try:
   d=json.loads(f.read_text());print('NEWS_CONFIG',str(f),json.dumps(d.get('providers',{})))
  except Exception:pass
