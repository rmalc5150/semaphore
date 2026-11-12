import subprocess,json
from pathlib import Path
import repair_individual as r
r.OUT=r.ROOT/'repair-notes/2026-10-23-checkup'
m=r.ROOT/'upgrade/t3-large/maintenance-state.json'
if m.exists():m.replace(r.OUT/'prior-maintenance-state.json')
with (r.OUT/'quiesce.log').open('ab',buffering=0)as f:
 subprocess.run([r.PYTHON,'upgrade/t3-large/prepare.py','quiesce'],cwd=r.ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
steps=[
 ('hkex-docx',['repair_checkup_hkex.py','manifests/collection_runs/source=hkex_news/dataset=filings/run_8d09a5de-879b-4561-9c80-a0751f9f4f6a/final.json'],360),
 ('hkex-removed',['repair_checkup_hkex.py','manifests/collection_runs/source=hkex_news/dataset=filings/run_451d5b33-1923-4219-afdd-a45df7ece17c/final.json'],360),
 ('hkex-history',['repair_checkup_hkex.py','manifests/collection_runs/source=hkex_news/dataset=filings/run_ee80505b-1afe-476d-9705-7c0823407a30/final.json'],360),
 ('clinicaltrials',['repair_checkup_ct.py'],240),
 ('nih',['repair_scope.py','historical','nih_reporter','--reason','nih_split_count_changed','--pages','1'],240),
 ('nmpa',['nmpa_baseline.py','inventory','2026-09-22','--max-pages','1'],240),
 ('athena',['committed_data_athena.py'],900),
 ('daily-audit',['daily_health_audit.py'],600)]
results=[]
try:
 for step in steps:
  x=r.execute(*step);results.append(x);r.save(r.OUT/'summary.json',results)
  if not x['checkpoint_verified']:raise RuntimeError('Unverified runtime checkpoint; stop before next job')
finally:
 if not Path('/dev/shm/optima-s3/pending.json').exists():
  with (r.OUT/'resume.log').open('ab',buffering=0)as f:
   code=subprocess.run([r.PYTHON,'upgrade/t3-large/prepare.py','resume'],cwd=r.ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
  r.save(r.OUT/'resume.json',{'exit_code':code})
