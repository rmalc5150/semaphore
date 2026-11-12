"""Install the m7 summary queue and replace t3 gap execution with enqueueing."""
import io,tarfile,json,hashlib,boto3
from pathlib import Path
from constellation.finish_aux_migration import remote,M7,T3,ROOT

def main():
    from constellation.m7_summary_queue import enqueue,Control
    c=Control();enqueue(c,'database');enqueue(c,'gaps')
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w:gz',dereference=True)as tar:
        for name in ('constellation/__init__.py','constellation/control.py','constellation/gaps.py','constellation/coverage_scope.py','constellation/m7_summary_queue.py','constellation/database_diagnostic.py','metadata_engine/runtime_db.py','reviewed_source_gaps.py','config/metadata-engine.json','config/rds-us-east-1-ca-bundle.pem','config/collection-gap-policy.json'):
            tar.add(ROOT/name,arcname=name)
        body=b'"""Read-only database client for isolated summary runtime."""\n'
        info=tarfile.TarInfo('metadata_engine/__init__.py');info.size=len(body);tar.addfile(info,io.BytesIO(body))
        config=json.loads((ROOT/'config/constellation-infrastructure.json').read_text());config.pop('controller_secret_arn',None)
        body=json.dumps(config).encode();info=tarfile.TarInfo('config/constellation-infrastructure.json');info.size=len(body);tar.addfile(info,io.BytesIO(body))
    body=buf.getvalue();sha=hashlib.sha256(body).hexdigest();key=c.config['prefix']+'/deployments/summary-worker-'+sha+'.tgz'
    c.s3.put_object(Bucket=c.config['bucket'],Key=key,Body=body,ServerSideEncryption='AES256')
    remote(M7,'''import boto3,hashlib,tarfile,io,os,subprocess
from pathlib import Path
body=boto3.client('s3',region_name='us-east-1').get_object(Bucket=BUCKET,Key=KEY)['Body'].read();assert hashlib.sha256(body).hexdigest()==SHA
root=Path('/opt/constellation/summary-worker');root.mkdir(exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(body),mode='r:gz')as tar:tar.extractall(root,filter='data')
(root/'worker.lock').touch()
for p in [root,*root.rglob('*')]:os.chown(p,1000,1000)
unit='[Unit]\\nDescription=Queued m7 gap audit and database summaries\\nAfter=network-online.target\\n[Service]\\nType=oneshot\\nUser=ec2-user\\nWorkingDirectory='+str(root)+'\\nExecStart=/opt/constellation/legacy-venv/bin/python -B -m constellation.m7_summary_queue work\\nEnvironment=CONSTELLATION_ROLE=worker\\nEnvironment=AWS_DEFAULT_REGION=us-east-1\\nSlice=constellation-workers.slice\\nCPUQuota=50%\\nCPUWeight=25\\nMemoryHigh=768M\\nMemoryMax=1G\\nMemorySwapMax=0\\nTimeoutStartSec=1h\\nNoNewPrivileges=true\\n'
Path('/etc/systemd/system/optima-m7-summary-worker.service').write_text(unit)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemd-analyze','verify','/etc/systemd/system/optima-m7-summary-worker.service'],check=True)
print('Summary worker installed')
'''.replace('BUCKET',repr(c.config['bucket'])).replace('KEY',repr(key)).replace('SHA',repr(sha)))
    remote(T3,'''from pathlib import Path
import subprocess
base=Path('/etc/systemd/system');python='/home/ec2-user/data-collection-processing/.venv-athena/bin/python'
folder=base/'constellation-gap-audit.service.d';folder.mkdir(exist_ok=True)
(folder/'zzzz-m7-queue.conf').write_text('[Service]\\nExecStart=\\nExecStart='+python+' -B -m constellation.m7_summary_queue gaps\\nTimeoutStartSec=10min\\nReadWritePaths=/home/ec2-user/data-collection-processing/constellation/autostop\\n')
for name,mode,interval in (('optima-m7-summary-poll','poll','5min'),('optima-m7-database-summary','database','6h')):
 (base/(name+'.service')).write_text('[Unit]\\nDescription=Queue or collect m7 summary work\\n[Service]\\nType=oneshot\\nUser=ec2-user\\nWorkingDirectory=/home/ec2-user/data-collection-processing\\nExecStart='+python+' -B -m constellation.m7_summary_queue '+mode+'\\nTimeoutStartSec=10min\\nMemoryMax=128M\\n')
 (base/(name+'.timer')).write_text('[Unit]\\nDescription=Schedule m7 summary requests and receipt collection\\n[Timer]\\nOnBootSec=2min\\nOnUnitInactiveSec='+interval+'\\n[Install]\\nWantedBy=timers.target\\n')
subprocess.run(['systemctl','stop','constellation-gap-audit.service'],check=True)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','optima-m7-summary-poll.timer','optima-m7-database-summary.timer'],check=True)
subprocess.run(['systemctl','start','--no-block','optima-m7-summary-poll.service'],check=True)
subprocess.run(['systemctl','start','--no-block','constellation-gap-audit.service'],check=True)
print('t3 now submits gap audits to durable queue; summary/poll timers enabled')
''')
if __name__=='__main__':main()
