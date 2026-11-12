"""Run one independently checkpointed public API daily source per t3 batch."""
from datetime import datetime,timezone
import json,os,subprocess
from pathlib import Path
from constellation.control import Control
from public_source_capture import PREFIX,read_json,put,encode
ROOT=Path(__file__).resolve().parents[1]

def main():
    control=Control()
    if not control.daily_allowed():return
    sources=[r['source'] for r in json.loads((ROOT/'constellation/expansion/new-adapters.json').read_text()) if r.get('daily_enabled',True)]
    key=PREFIX+'/daily-api-fairness.json';state,token=read_json(control.s3,key);state=state or {'sources':{}}
    source=min(sources,key=lambda s:(state['sources'].get(s,''),s))
    root=ROOT/'constellation/daily-workspaces'/source
    ram=Path('/dev/shm/constellation-public-api')/source
    (ram/'locks').mkdir(parents=True,exist_ok=True)
    for name in ('reports','mlperf-evidence-cache','ted-package-cache','collection-output'):
        link=root/name
        if not link.is_symlink():link.symlink_to(ram/'work'/name,target_is_directory=True)
    env=dict(os.environ,OPTIMA_S3_RUNTIME_ROOT=str(root),OPTIMA_S3_RUNTIME_BASE='/dev/shm/constellation-public-api/'+source,
        OPTIMA_S3_RUNTIME_PREFIX=control.config['prefix']+'/daily-api-runtime/'+source,OPTIMA_S3_RUNTIME='0',
        CONSTELLATION_ROLE='controller',CONSTELLATION_SHARED_HTTP_LIMITS='1',PYTHONPATH=str(root),
        CONSTELLATION_SPECIALIST_PLAN=str(root/'config/constellation-specialist-historical.json'),
        CONSTELLATION_SPECIALIST_SCHEDULER_PREFIX='constellation-backfill/daily-api-schedulers/'+source,
        CONSTELLATION_OPERATION_RECEIPT_PREFIX='constellation-backfill/daily-api-receipts/'+source,
        CONSTELLATION_VERIFY_MISSING_S3_KEYS='1',PYTHONDONTWRITEBYTECODE='1')
    python=str(ROOT/'.venv-athena/bin/python')
    command=[python,'-B',str(root/'s3_runtime.py'),'--unit','constellation-public-api-'+source+'.service','--',python,'-B',str(root/'specialist_inputs.py'),'--mode','daily','--source',source,'--max-jobs','2','--pages','2','--publish','0']
    result=subprocess.run(command,cwd=root,env=env)
    state['sources'][source]=datetime.now(timezone.utc).isoformat();put(control.s3,key,encode(state),**({'IfMatch':token} if token else {'IfNoneMatch':'*'}))
    print(json.dumps({'daily_api_source':source,'exit_code':result.returncode}),flush=True)
    return result.returncode

if __name__=='__main__':raise SystemExit(main())
