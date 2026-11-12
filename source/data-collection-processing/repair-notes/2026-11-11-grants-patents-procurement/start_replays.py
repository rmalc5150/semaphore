import json,base64,hashlib,boto3
from pathlib import Path
p=Path(__file__).parent;sources=json.loads((p/'sources.json').read_text());template=Path('repair-notes/2026-11-09-hkex-repair/replay_verified.py').read_text();files={};c=json.load(open('config/constellation-infrastructure.json'));s=boto3.client('s3',region_name=c['region'])
for source in sources:
 ids=tuple(json.loads((p/source/'migration.json').read_text())['repair_job_ids']);runner=template;start=runner.index('IDS=');end=runner.index('\nconfig=',start);runner=runner[:start]+'IDS='+repr(ids)+runner[end:];runner=runner.replace('hkex_news',source).replace('range(4)','range(len(IDS))').replace(' AND available_after<=UTC_TIMESTAMP(6)','');(p/source/'replay_verified.py').write_text(runner);raw=runner.encode();sha=hashlib.sha256(raw).hexdigest();key=c['prefix']+'/deployments/grants-patents-validation-20261111/'+sha+'/'+source+'_replay.py';s.put_object(Bucket=c['bucket'],Key=key,Body=raw,ServerSideEncryption='AES256');files[source]={'key':key,'sha256':sha}
script='''import boto3,hashlib,subprocess,json,concurrent.futures
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');root=Path('/opt/constellation/metadata-engine-runtime')
for source,ref in FILES.items():
 raw=s.get_object(Bucket=BUCKET,Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];(root/(source+'_replay.py')).write_bytes(raw)
def run(source):
 name='optima-'+source.replace('_','-')+'-review-replay-v2';cmd=['systemd-run','--unit='+name,'--wait','--property=User=ec2-user','--property=WorkingDirectory='+str(root),'--property=Slice=constellation-workers.slice','--property=MemoryMax=536870912','--property=CPUQuota=25%','--property=RuntimeMaxSec=330','/opt/constellation/legacy-venv/bin/python','-B',source+'_replay.py'];r=subprocess.run(cmd,capture_output=True,text=True);out={'source':source,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'journal':subprocess.run(['journalctl','-u',name,'--no-pager','-n','8'],capture_output=True,text=True).stdout};print(json.dumps(out),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:list(pool.map(run,FILES))
'''.replace('FILES',repr(files)).replace('BUCKET',repr(c['bucket']));(p/'run_replays_remote.py').write_text(script)
