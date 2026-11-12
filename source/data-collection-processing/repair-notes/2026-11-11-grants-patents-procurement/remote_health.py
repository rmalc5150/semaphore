import subprocess,json
from pathlib import Path
root=Path('/opt/constellation/source')
for f in ('config/company-universe.v0.3.json','config/company-universe.v0.5.json','config/google-patents-aws.json','nist-robotics.sqlite3'):
 p=root/f;print(f,'exists',p.exists(),'link',str(p.resolve()))
print(subprocess.run(['systemctl','list-timers','*constellation*','--all','--no-pager'],capture_output=True,text=True).stdout[:5000])
for name in ('config/constellation-specialist-historical.json','config/constellation-native-historical.json','config/constellation-legacy-routes.json'):
 p=root/name
 if p.exists():
  d=json.loads(p.read_text());print(name,json.dumps(d)[:1000])
