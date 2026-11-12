import json,subprocess
from pathlib import Path
import repair_individual as r
r.OUT=r.ROOT/'repair-notes/2026-10-21-news-patents-disclosures'
steps=[('news',['news_operations.py'],360),('patents',['patent_operations.py','daily','--max-pages','6','--max-windows','1'],360),('prosecution-history',['patent_prosecution_operations.py','historical'],360),('prosecution-daily',['patent_prosecution_operations.py','daily'],240),('disclosures',['collect_daily.py','--only','press-releases','--only','licensing-agreements','--only','ma-announcements','--only','strategic-transactions','--max-windows','3','--max-pages','3'],900)]
results=[]
try:
 for step in steps:
  x=r.execute(*step);results.append(x);r.save(r.OUT/'summary.json',results)
  if not x['checkpoint_verified']:raise RuntimeError('Unverified checkpoint')
finally:
 if not Path('/dev/shm/optima-s3/pending.json').exists():
  with (r.OUT/'resume.log').open('ab',buffering=0)as f:code=subprocess.run([r.PYTHON,'upgrade/t3-large/prepare.py','resume'],cwd=r.ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
  r.save(r.OUT/'resume.json',{'exit_code':code})
