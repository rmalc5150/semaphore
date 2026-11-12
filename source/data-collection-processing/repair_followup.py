from pathlib import Path
import subprocess
from repair_individual import execute,ROOT,PYTHON,OUT,save
try:
 results=[]
 for step in [
  ('eia-generators-retry',['specialist_inputs.py','--mode','daily','--source','eia_battery_generators','--max-jobs','1','--pages','1','--publish','0'],240),
  ('eia-generator-publication',['repair_eia_publication.py'],300),
  ('patent-partition-retry',['patent_operations.py','daily','--max-pages','4','--max-windows','1'],240)]:
  result=execute(*step);results.append(result);save(OUT/'followup-summary.json',results)
  if not result['checkpoint_verified']:raise RuntimeError('Unverified checkpoint')
finally:
 if not Path('/dev/shm/optima-s3/pending.json').exists():
  with (OUT/'followup-resume.log').open('ab',buffering=0) as log:
   code=subprocess.run([PYTHON,'upgrade/t3-large/prepare.py','resume'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
  save(OUT/'followup-resume.json',{'exit_code':code})
