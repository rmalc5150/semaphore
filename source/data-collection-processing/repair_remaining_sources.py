"""Bounded individual retries with durable per-attempt results and schedule restore."""
import json,subprocess
from pathlib import Path
import repair_individual as runner
from collection_storage import StorageSettings
ROOT=Path(__file__).resolve().parent
runner.OUT=ROOT/'repair-notes/2026-10-21-remaining-sources'

def main():
 results=[]
 try:
  for name,lane,source,limit in [
   ('caiso','daily','caiso_prices',1),
   ('pmc','historical','europe_pmc_fulltext',1),
   ('mlperf','historical','mlperf_results',1),
   ('assignments','daily','uspto_assignment_histories',4),
   ('sam','authenticated-historical','sam_gov_opportunities',11)]:
   for attempt in range(1,limit+1):
    r=runner.execute(f'{name}-{attempt:02}', ['repair_scope.py',lane,source,'--pages','2'],240)
    results.append(r);runner.save(runner.OUT/'summary.json',results)
    if not r['checkpoint_verified']:raise RuntimeError('Unverified runtime checkpoint; stop')
    events=r['events']
    if any(e.get('status')=='no_matching_failed_scope' for e in events if isinstance(e,dict)):break
    failures=[e['capture'] for e in events if isinstance(e,dict) and 'capture' in e and e['capture'].get('status')=='failed']
    if failures or r['exit_code']:break
  for name,args,seconds in [('eia-publication',['repair_eia_publication.py'],600),('athena-publication',['committed_data_athena.py'],1800)]:
   r=runner.execute(name,args,seconds);results.append(r);runner.save(runner.OUT/'summary.json',results)
   if not r['checkpoint_verified']:raise RuntimeError('Unverified runtime checkpoint; stop')
 finally:
  if not Path('/dev/shm/optima-s3/pending.json').exists():
   with (runner.OUT/'resume.log').open('ab',buffering=0) as f:
    code=subprocess.run([runner.PYTHON,'upgrade/t3-large/prepare.py','resume'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
   runner.save(runner.OUT/'resume.json',{'exit_code':code})
if __name__=='__main__':main()
