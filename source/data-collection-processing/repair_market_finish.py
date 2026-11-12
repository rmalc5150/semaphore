import subprocess
from pathlib import Path
import repair_individual as r
r.OUT=r.ROOT/'repair-notes/2026-10-21-market-coverage'
m=r.ROOT/'upgrade/t3-large/maintenance-state.json'
m.replace(r.OUT/'maintenance-before-replay.json')
with (r.OUT/'replay-quiesce.log').open('ab',buffering=0)as f:
 subprocess.run([r.PYTHON,'upgrade/t3-large/prepare.py','quiesce'],cwd=r.ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
try:
 x=r.execute('mapping-replay',['repair_market_replay.py'],600)
 if not x['checkpoint_verified']:raise RuntimeError('Checkpoint unverified')
 x=r.execute('market-shared-athena',['committed_data_athena.py'],1200)
 if not x['checkpoint_verified']:raise RuntimeError('Checkpoint unverified')
finally:
 if not Path('/dev/shm/optima-s3/pending.json').exists():
  with (r.OUT/'replay-resume.log').open('ab',buffering=0)as f:
   c=subprocess.run([r.PYTHON,'upgrade/t3-large/prepare.py','resume'],cwd=r.ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
  r.save(r.OUT/'replay-resume.json',{'exit_code':c})
