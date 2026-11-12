import subprocess,json
from pathlib import Path
import repair_individual as r
r.OUT=r.ROOT/'repair-notes/2026-10-23-uspto-exception'
m=r.ROOT/'upgrade/t3-large/maintenance-state.json'
if m.exists():m.replace(r.OUT/'prior-maintenance-state.json')
with (r.OUT/'quiesce.log').open('ab',buffering=0) as f:
 subprocess.run([r.PYTHON,'upgrade/t3-large/prepare.py','quiesce'],cwd=r.ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
try:
 for name,args,timeout in [('exception-replay-priority',['repair_uspto_exception.py'],300),('exception-athena',['committed_data_athena.py'],900)]:
  x=r.execute(name,args,timeout)
  if not x['checkpoint_verified'] or x['exit_code']:raise RuntimeError('Step not verified: '+name)
finally:
 if not Path('/dev/shm/optima-s3/pending.json').exists():
  with (r.OUT/'resume.log').open('ab',buffering=0) as f:
   code=subprocess.run([r.PYTHON,'upgrade/t3-large/prepare.py','resume'],cwd=r.ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
  r.save(r.OUT/'resume.json',{'exit_code':code})
