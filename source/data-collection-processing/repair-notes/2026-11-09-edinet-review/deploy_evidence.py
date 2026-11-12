import base64,hashlib,json,boto3
from pathlib import Path
from metadata_engine.runtime_db import Database
p=Path(__file__).parent;config=json.load(open('config/metadata-engine.json'));db=Database(config)
with db.tx()as c:
 c.execute("SELECT job_id FROM engine_jobs WHERE source_key='edinet_filings' AND state='retry' AND reason='RuntimeError:larger_artifact_requires_streaming_adapter'");ids=tuple(r['job_id']for r in c.fetchall())
(p/'retry-ids.json').write_text(json.dumps(ids,indent=2))
runner=Path('repair-notes/2026-11-09-hkex-repair/replay_verified.py').read_text();start=runner.index('IDS=');end=runner.index('\nconfig=',start);runner=runner[:start]+'IDS='+repr(ids)+runner[end:];runner=runner.replace('HKEX','EDINET').replace('hkex_news','edinet_filings').replace('range(4)','range(len(IDS))').replace(' AND available_after<=UTC_TIMESTAMP(6)','');(p/'replay_verified.py').write_text(runner)
c=json.load(open('config/constellation-infrastructure.json'));s=boto3.client('s3',region_name=c['region']);files={}
for target,raw in [('metadata_engine/evidence.py',Path('metadata_engine/evidence.py').read_bytes()),('edinet_replay_verified.py',runner.encode())]:
 sha=hashlib.sha256(raw).hexdigest();key=c['prefix']+'/deployments/edinet-review-20261109/'+sha+'/'+target;s.put_object(Bucket=c['bucket'],Key=key,Body=raw,ServerSideEncryption='AES256');files[target]={'key':key,'sha256':sha}
code='''import boto3,json,hashlib,os
from pathlib import Path
files=FILES;root=Path('/opt/constellation/metadata-engine-runtime');s=boto3.client('s3',region_name='us-east-1')
for name,meta in files.items():
 raw=s.get_object(Bucket=BUCKET,Key=meta['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==meta['sha256'];compile(raw,name,'exec');target=root/name
 backup=Path('/opt/constellation/tmp/edinet-review-evidence-backup')/name;backup.parent.mkdir(parents=True,exist_ok=True)
 if target.exists() and not backup.exists():backup.write_bytes(target.read_bytes())
 temp=target.with_suffix('.repair.tmp');temp.write_bytes(raw);os.chmod(temp,0o644);temp.replace(target)
p=root/'config/metadata-engine.json';d=json.loads(p.read_text());d['build_sha256']=hashlib.sha256(b''.join(x.read_bytes()for x in sorted((root/'metadata_engine').glob('*.py')))+(root/'hkex_originals.py').read_bytes()).hexdigest();tmp=p.with_suffix('.repair.tmp');tmp.write_text(json.dumps(d,indent=2));tmp.replace(p)
print(json.dumps({'deployed':list(files),'build_sha256':d['build_sha256']}))
'''.replace('FILES',repr(files)).replace('BUCKET',repr(c['bucket']))
enc=base64.b64encode(code.encode()).decode();cmd="/opt/constellation/legacy-venv/bin/python -c \"import base64;exec(base64.b64decode('"+enc+"'))\"\nsystemd-run --unit=optima-edinet-verified-replay-v2 --wait --property=User=ec2-user --property=WorkingDirectory=/opt/constellation/metadata-engine-runtime --property=Slice=constellation-workers.slice --property=MemoryMax=536870912 --property=CPUQuota=25% --property=RuntimeMaxSec=360 /opt/constellation/legacy-venv/bin/python -B edinet_replay_verified.py"
r=boto3.client('ssm',region_name=c['region']).send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=420);(p/'evidence-deployment-command.json').write_text(json.dumps({'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id'],'files':files},indent=2));print(r['Command']['CommandId'],len(ids),'validated-cause retries')
