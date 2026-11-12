"""Detached, per-step durable logs and runtime checkpoints for bounded repairs."""
import json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PYTHON=str(ROOT/'.venv-athena/bin/python')
OUT=ROOT/'repair-notes/2026-10-21-individual-replays'

def save(path,value):
    tmp=path.with_suffix('.pending')
    with tmp.open('w') as f:
        json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    tmp.replace(path)

def execute(name,args,seconds):
    result={'step':name,'command':args,'started_at':datetime.now(timezone.utc).isoformat(),'status':'running'}
    save(OUT/(name+'.json'),result)
    command=['/usr/bin/flock','--exclusive','--timeout','60','/dev/shm/optima-s3/supervisor.lock',PYTHON,'-u','-B',str(ROOT/'s3_runtime.py'),'--unit','repair-'+name,'--','/usr/bin/timeout','--signal=INT','--kill-after=120s',str(seconds),PYTHON,'-u','-B',*args]
    with (OUT/(name+'.log')).open('ab',buffering=0) as log:
        code=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
    events=[]
    for line in (OUT/(name+'.log')).read_text(errors='replace').splitlines():
        try:events.append(json.loads(line))
        except ValueError:pass
    result.update(exit_code=code,finished_at=datetime.now(timezone.utc).isoformat(),
        checkpoint_verified=any(isinstance(e,dict) and e.get('stage')=='s3_checkpoint_verified' and e.get('unit')=='repair-'+name for e in events),
        status='execution_completed' if code==0 else 'needs_attention',events=events)
    # Exit zero only means execution completed. Capture/publication statuses stay explicit.
    save(OUT/(name+'.json'),result)
    print(json.dumps({k:v for k,v in result.items() if k!='events'}),flush=True)
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    steps=[
      ('pmc',['repair_scope.py','historical','europe_pmc_fulltext','--reason','source_retries_exhausted','--pages','1'],240),
      ('caiso',['repair_scope.py','daily','caiso_prices','--reason','caiso_columns','--pages','2'],180),
      ('sam',['repair_scope.py','authenticated-historical','sam_gov_opportunities','--pages','1'],180),
      ('assignments',['repair_scope.py','daily','uspto_assignment_histories','--pages','2'],180),
      ('mlperf',['repair_scope.py','historical','mlperf_results','--pages','1'],180),
      ('eia-retail',['repair_scope.py','authenticated-historical','eia_retail_prices','--pages','4'],240),
      ('eia-generators',['specialist_inputs.py','--mode','daily','--source','eia_battery_generators','--max-jobs','1','--pages','1','--publish','0'],240),
      ('patents',['patent_operations.py','daily','--max-pages','2','--max-windows','1'],240),
      ('prosecution',['patent_prosecution_operations.py','daily'],240),
      ('news',['news_operations.py'],240),
      ('core-publication',['repair_core_publication.py'],900),
      ('athena',['committed_data_athena.py'],1800)]
    results=[]
    try:
        for step in steps:
            result=execute(*step);results.append(result)
            save(OUT/'summary.json',results)
            if not result['checkpoint_verified']:
                raise RuntimeError('Checkpoint not verified; retain RAM and stop before next step')
    finally:
        # Restore only schedules active at entry; explicitly paused sources stay stopped.
        if not Path('/dev/shm/optima-s3/pending.json').exists():
            with (OUT/'resume.log').open('ab',buffering=0) as log:
                code=subprocess.run([PYTHON,'upgrade/t3-large/prepare.py','resume'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
            save(OUT/'resume.json',{'exit_code':code})
if __name__=='__main__':main()
