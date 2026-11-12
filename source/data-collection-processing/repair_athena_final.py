from pathlib import Path
import subprocess
from repair_individual import execute,ROOT,PYTHON,OUT,save
try:
 result=execute('athena-final',['committed_data_athena.py'],1800)
 save(OUT/'final-pass.json',result)
finally:
 if not Path('/dev/shm/optima-s3/pending.json').exists():
  with (OUT/'final-resume.log').open('ab',buffering=0) as log:
   code=subprocess.run([PYTHON,'upgrade/t3-large/prepare.py','resume'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
  save(OUT/'final-resume.json',{'exit_code':code})
