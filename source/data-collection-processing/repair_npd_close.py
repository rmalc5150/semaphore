import subprocess,time
import repair_individual as r
r.OUT=r.ROOT/'repair-notes/2026-10-21-news-patents-disclosures'
for _ in range(240):
 state=subprocess.run(['systemctl','is-active','optima-news-patents-disclosures-final.service'],capture_output=True,text=True).stdout.strip()
 if state not in ('active','activating','deactivating'):break
 time.sleep(5)
else:raise RuntimeError('Earlier repair still running')
for step in [('dependency-reconciliation',['repair_npd_reconcile.py'],240),('closing-audit',['repair_npd_audit.py'],240)]:
 result=r.execute(*step)
 if not result['checkpoint_verified']:raise RuntimeError('Checkpoint unverified')
