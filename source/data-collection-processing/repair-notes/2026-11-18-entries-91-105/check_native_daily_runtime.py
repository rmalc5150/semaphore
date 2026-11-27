from ops import *
code=r'''import json,subprocess,os
from pathlib import Path
root=Path.cwd();source='cninfo_mainland_china_company_disclosures';work=root/'constellation/daily-workspaces'/source;script=work/'review_daily_check.py'
script.write_text("""import os,subprocess
from pathlib import Path
root=Path.cwd();source='cninfo_mainland_china_company_disclosures';ram=Path('/dev/shm/constellation-public-api')/source;(ram/'locks').mkdir(parents=True,exist_ok=True)
for name in ('reports','mlperf-evidence-cache','ted-package-cache','collection-output'):
 target=ram/'work'/name;target.mkdir(parents=True,exist_ok=True);link=root/name
 if not link.exists():link.symlink_to(target,target_is_directory=True)
env=dict(os.environ,OPTIMA_S3_RUNTIME_ROOT=str(root),OPTIMA_S3_RUNTIME_BASE=str(ram),OPTIMA_S3_RUNTIME_PREFIX='research-data/constellation-backfill/daily-api-runtime/'+source,OPTIMA_S3_RUNTIME='0',CONSTELLATION_ROLE='controller',CONSTELLATION_SHARED_HTTP_LIMITS='1',PYTHONPATH=str(root),CONSTELLATION_SPECIALIST_PLAN=str(root/'config/constellation-specialist-historical.json'),CONSTELLATION_SPECIALIST_SCHEDULER_PREFIX='constellation-backfill/daily-api-schedulers/'+source,CONSTELLATION_OPERATION_RECEIPT_PREFIX='constellation-backfill/daily-api-receipts/'+source,CONSTELLATION_VERIFY_MISSING_S3_KEYS='1',PYTHONDONTWRITEBYTECODE='1')
python='/home/ec2-user/data-collection-processing/.venv-athena/bin/python';raise SystemExit(subprocess.call([python,'-B',str(root/'s3_runtime.py'),'--unit','constellation-public-api-'+source+'.service','--',python,'-B',str(root/'specialist_inputs.py'),'--mode','daily','--source',source,'--max-jobs','1','--pages','1','--publish','0'],cwd=root,env=env))
""");os.chown(script,1000,1000)
subprocess.run(['systemd-run','--unit=constellation-review-cninfo-daily-runtime','--no-block','--collect','-p','User=ec2-user','-p','WorkingDirectory='+str(work),'-p','MemoryMax=384M','-p','CPUQuota=50%','-p','RuntimeMaxSec=600','-p','Environment=AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_DEFAULT_REGION=us-east-1','/home/ec2-user/data-collection-processing/.venv-athena/bin/python','-B',str(script)],check=True);print('Started bounded CNINFO check through its actual daily runtime workspace.')
'''
print(remote(T3,code)['out'])
