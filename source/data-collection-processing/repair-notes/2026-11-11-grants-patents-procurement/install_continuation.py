import boto3,json,hashlib,base64,subprocess,time
from pathlib import Path
p=Path(__file__).parent;c=json.load(open('config/constellation-infrastructure.json'));s=boto3.client('s3',region_name=c['region']);raw=Path('metadata_engine/reviewed_continuation.py').read_bytes();sha=hashlib.sha256(raw).hexdigest();key=c['prefix']+'/deployments/grants-patents-validation-20261111/'+sha+'/reviewed_continuation.py';s.put_object(Bucket=c['bucket'],Key=key,Body=raw,ServerSideEncryption='AES256')
coordinator='''import concurrent.futures,subprocess,json
from metadata_engine.reviewed_continuation import SOURCES
def run(source):
 unit='optima-reviewed-metadata-'+source.replace('_','-');result=subprocess.run(['systemd-run','--unit='+unit,'--collect','--wait','--property=User=ec2-user','--property=WorkingDirectory=/opt/constellation/metadata-engine-runtime','--property=Slice=constellation-workers.slice','--property=MemoryMax=536870912','--property=CPUQuota=20%','--property=RuntimeMaxSec=180','/opt/constellation/legacy-venv/bin/python','-B','-m','metadata_engine.reviewed_continuation','--source',source],capture_output=True,text=True);print(json.dumps({'source':source,'returncode':result.returncode,'stderr':result.stderr[-600:]}),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:list(pool.map(run,SOURCES))
'''
unit='[Unit]\nDescription=Continue reviewed source metadata with independent leases and two-worker cap\nAfter=network-online.target\n[Service]\nType=oneshot\nWorkingDirectory=/opt/constellation/metadata-engine-runtime\nExecStart=/opt/constellation/legacy-venv/bin/python -B reviewed_coordinator.py\nMemoryMax=134217728\nCPUQuota=10%\nTimeoutStartSec=780\n';timer='[Unit]\nDescription=Continue reviewed source metadata\n[Timer]\nOnBootSec=120\nOnUnitInactiveSec=120\nUnit=optima-reviewed-metadata-continuation.service\n[Install]\nWantedBy=timers.target\n'
script='''import boto3,hashlib,subprocess,json
from pathlib import Path
root=Path('/opt/constellation/metadata-engine-runtime');raw=boto3.client('s3',region_name='us-east-1').get_object(Bucket=BUCKET,Key=KEY)['Body'].read();assert hashlib.sha256(raw).hexdigest()==SHA;target=root/'metadata_engine/reviewed_continuation.py';temp=target.with_suffix('.tmp');temp.write_bytes(raw);temp.replace(target);(root/'reviewed_coordinator.py').write_text(COORDINATOR)
p=root/'config/metadata-engine.json';d=json.loads(p.read_text());d['build_sha256']=hashlib.sha256(b''.join(x.read_bytes()for x in sorted((root/'metadata_engine').glob('*.py')))+(root/'hkex_originals.py').read_bytes()).hexdigest();temp=p.with_suffix('.tmp');temp.write_text(json.dumps(d,indent=2));temp.replace(p)
Path('/etc/systemd/system/optima-reviewed-metadata-continuation.service').write_text(UNIT);Path('/etc/systemd/system/optima-reviewed-metadata-continuation.timer').write_text(TIMER);subprocess.run(['systemctl','daemon-reload'],check=True);subprocess.run(['systemctl','enable','--now','optima-reviewed-metadata-continuation.timer'],check=True);subprocess.run(['systemctl','start','--no-block','optima-reviewed-metadata-continuation.service'],check=True)
'''
for a,b in {'BUCKET':repr(c['bucket']),'KEY':repr(key),'SHA':repr(sha),'COORDINATOR':repr(coordinator),'UNIT':repr(unit),'TIMER':repr(timer)}.items():script=script.replace(a,b)
(p/'install_continuation_remote.py').write_text(script)
# A separate controller publisher; no notifications are sent.
base='optima-reviewed-metadata-publication';unit='[Unit]\nDescription=Publish reviewed source metadata independently\nAfter=network-online.target\n[Service]\nType=oneshot\nUser=ec2-user\nWorkingDirectory=/home/ec2-user/data-collection-processing\nExecStart=/home/ec2-user/data-collection-processing/.venv-athena/bin/python -B reviewed_metadata_publication.py\nSlice=optima-financial.slice\nMemoryMax=201326592\nCPUQuota=15%\nTimeoutStartSec=300\n';timer='[Unit]\nDescription=Continue reviewed metadata publication\n[Timer]\nOnBootSec=120\nOnUnitInactiveSec=120\nUnit='+base+'.service\n[Install]\nWantedBy=timers.target\n'
for suffix,body in (('.service',unit),('.timer',timer)):
 file=p/(base+suffix);file.write_text(body);subprocess.run(['sudo','install','-m','0644',str(file),'/etc/systemd/system/'+file.name],check=True)
subprocess.run(['sudo','systemctl','daemon-reload'],check=True);subprocess.run(['sudo','systemctl','enable','--now',base+'.timer'],check=True)
