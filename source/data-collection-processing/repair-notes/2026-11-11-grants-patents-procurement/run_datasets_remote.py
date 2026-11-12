import boto3,hashlib,subprocess,json,concurrent.futures
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');root=Path('/opt/constellation/metadata-engine-runtime')
files={'ted_notices': {'key': 'research-data/constellation-backfill/deployments/grants-patents-validation-20261111/eaadfdf49a00064e0cc4cd1a3a043522ce7dd58407a6717879db21f2cef6fea3/ted_notices_replay.py', 'sha256': 'eaadfdf49a00064e0cc4cd1a3a043522ce7dd58407a6717879db21f2cef6fea3'}, 'uspto_odp': {'key': 'research-data/constellation-backfill/deployments/grants-patents-validation-20261111/a1a7d367fc6ab43c6e90dfdc125eb6908415985153a6c0158ffedb93a0a6349b/uspto_odp_replay.py', 'sha256': 'a1a7d367fc6ab43c6e90dfdc125eb6908415985153a6c0158ffedb93a0a6349b'}}
for source,ref in files.items():
 raw=s.get_object(Bucket='data-collection-059416028963-us-east-1-an',Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];(root/(source+'_replay.py')).write_bytes(raw)
def run(source):
 name='optima-'+source.replace('_','-')+'-dataset-replay-v2';cmd=['systemd-run','--unit='+name,'--wait','--property=User=ec2-user','--property=WorkingDirectory='+str(root),'--property=Slice=constellation-workers.slice','--property=MemoryMax=536870912','--property=CPUQuota=25%','--property=RuntimeMaxSec=330','/opt/constellation/legacy-venv/bin/python','-B',source+'_replay.py'];r=subprocess.run(cmd,capture_output=True,text=True);out={'source':source,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'journal':subprocess.run(['journalctl','-u',name,'--no-pager','-n','8'],capture_output=True,text=True).stdout};print(json.dumps(out),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:list(pool.map(run,files))
