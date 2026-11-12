import json,subprocess,time
from pathlib import Path
import repair_individual as r
r.OUT=r.ROOT/'repair-notes/2026-10-21-news-patents-disclosures'
for _ in range(60):
 state=subprocess.run(['systemctl','is-active','optima-news-patents-disclosures-repair.service'],capture_output=True,text=True).stdout.strip()
 if state not in ('active','activating','deactivating'):break
 time.sleep(5)
else:raise RuntimeError('Earlier repair is still active')
maintenance=r.ROOT/'upgrade/t3-large/maintenance-state.json'
maintenance.replace(r.OUT/'maintenance-before-fixed-replay.json')
with (r.OUT/'fixed-quiesce.log').open('ab',buffering=0)as f:
 subprocess.run([r.PYTHON,'upgrade/t3-large/prepare.py','quiesce'],cwd=r.ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
results=[]
try:
 for step in [
  ('disclosures-fixed',['collect_daily.py','2026-09-21','--only','press-releases','--only','licensing-agreements','--only','ma-announcements','--only','strategic-transactions','--max-windows','1','--max-pages','10'],1200),
  ('targeted-publication',['repair_npd_publish.py'],900),
  ('athena-publication',['committed_data_athena.py'],1800),
  ('audit-after',['repair_npd_audit.py'],240)]:
  x=r.execute(*step);results.append(x);r.save(r.OUT/'fixed-summary.json',results)
  if not x['checkpoint_verified']:raise RuntimeError('Unverified checkpoint')
finally:
 if not Path('/dev/shm/optima-s3/pending.json').exists():
  with (r.OUT/'fixed-resume.log').open('ab',buffering=0)as f:code=subprocess.run([r.PYTHON,'upgrade/t3-large/prepare.py','resume'],cwd=r.ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
  r.save(r.OUT/'fixed-resume.json',{'exit_code':code})
