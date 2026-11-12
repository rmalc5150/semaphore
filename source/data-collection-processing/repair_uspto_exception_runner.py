import subprocess
import repair_individual as r
r.OUT=r.ROOT/'repair-notes/2026-10-23-uspto-exception'
try:
 x=r.execute('exception-replay',['repair_uspto_exception.py'],300)
 if not x['checkpoint_verified'] or x['exit_code']:raise RuntimeError('Replay not verified')
 x=r.execute('exception-athena',['committed_data_athena.py'],900)
 if not x['checkpoint_verified'] or x['exit_code']:raise RuntimeError('Athena not verified')
finally:
 subprocess.run(['sudo','systemctl','reset-failed','optima-patents-prosecution.service'])
 subprocess.run(['sudo','systemctl','start','--no-block','optima-patents-prosecution.service'])
