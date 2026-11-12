"""Move remaining portable processing lanes to the shared m7 executor."""
import boto3,json,hashlib
from pathlib import Path
from constellation.finish_aux_migration import remote,M7,T3,ROOT
JOBS={'committed-athena':'committed_data_athena.py','cms-catalog-publication':'cms_catalog_publication.py','fda-reviewed-publication':'fda_review_publication.py','grants-reviewed-publication':'grants_review_publication.py','reviewed-metadata-publication':'reviewed_metadata_publication.py','patents-prosecution-publication':'research_publication.py --owners patent_office_actions patent_petition_decisions --max-windows 1','collection-daily':'collect_daily.py --max-windows 1 --max-pages 1 --reconcile-days 3'}
def main():
 remote(T3,'''import subprocess
subprocess.run(['systemctl','stop','optima-committed-athena.service'],check=True)
print('Controller committed-Athena stopped for index handoff')
''')
 s=boto3.client('s3',region_name='us-east-1');bucket='data-collection-059416028963-us-east-1-an'
 manifest=json.loads(s.get_object(Bucket=bucket,Key='research-data/operations/s3-runtime/current.json')['Body'].read())
 entry=manifest['paths'].get('committed-athena-index.sqlite3')
 assert entry,'Committed index snapshot missing; preserve state before migration'
 dest='research-data/constellation-backfill/deployments/committed-index-'+entry['sha256']+'.sqlite3'
 s.copy_object(Bucket=bucket,Key=dest,CopySource={'Bucket':bucket,'Key':entry['key']},ServerSideEncryption='AES256')
 code=(ROOT/'committed_data_athena.py').read_bytes();key='research-data/constellation-backfill/deployments/committed-code-'+hashlib.sha256(code).hexdigest()+'.py';s.put_object(Bucket=bucket,Key=key,Body=code,ServerSideEncryption='AES256')
 remote(M7,'''from pathlib import Path
import boto3,hashlib,subprocess,os
root=Path('/opt/constellation/auxiliary-publication/source');s=boto3.client('s3',region_name='us-east-1')
code=s.get_object(Bucket=BUCKET,Key=CODE)['Body'].read();p=root/'committed_data_athena.py';p.write_bytes(code);os.chown(p,1000,1000)
index=root/'committed-athena-index.sqlite3'
if not index.exists():
 s.download_file(BUCKET,INDEX,str(index));assert hashlib.sha256(index.read_bytes()).hexdigest()==DIGEST;os.chown(index,1000,1000)
(root/'reports').mkdir(exist_ok=True)
try:s.download_file(BUCKET,'research-data/athena-committed/latest-report.json',str(root/'reports/committed-athena-latest.json'));os.chown(root/'reports/committed-athena-latest.json',1000,1000)
except s.exceptions.NoSuchKey:pass
for name,argv in JOBS.items():
 unit='optima-m7-committed-athena.service'if name=='committed-athena'else 'optima-m7-aux-'+name+'.service'
 prefix=''if name in ('committed-athena','collection-daily')else '/usr/bin/flock /opt/constellation/auxiliary-publication/publish.lock '
 text='[Unit]\\nDescription=Optima m7 processing '+name+'\\nAfter=network-online.target\\n[Service]\\nType=oneshot\\nUser=ec2-user\\nWorkingDirectory='+str(root)+'\\nExecStart='+prefix+'/opt/constellation/legacy-venv/bin/python -B '+argv+'\\nSlice=constellation-workers.slice\\nCPUQuota=100%\\nMemoryHigh=2G\\nMemoryMax=3G\\nMemorySwapMax=0\\nTimeoutStartSec=6h\\nSuccessExitStatus=2\\nEnvironment=AWS_DEFAULT_REGION=us-east-1\\nEnvironment=PYTHONDONTWRITEBYTECODE=1\\nEnvironment=ARROW_NUM_THREADS=1\\n'
 Path('/etc/systemd/system/'+unit).write_text(text)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','start','--no-block','optima-m7-committed-athena.service'],check=True)
for unit in ('optima-grants-reviewed-capture.service','optima-nih-reviewed-historical.service','optima-m7-aux-news-publication.service'):
 subprocess.run(['systemctl','restart','--no-block',unit],check=True)
print('m7 processing units installed; committed verifier and inode-failed workers started')
'''.replace('BUCKET',repr(bucket)).replace('Key=CODE','Key='+repr(key)).replace('INDEX',repr(dest)).replace('DIGEST',repr(entry['sha256'])).replace('JOBS',repr(JOBS)))
 remote(T3,'''from pathlib import Path
import subprocess
for name in JOBS:
 unit='optima-'+name+'.service';folder=Path('/etc/systemd/system/'+unit+'.d');folder.mkdir(exist_ok=True)
 target='optima-m7-committed-athena.service'if name=='committed-athena'else 'optima-m7-aux-'+name+'.service'
 (folder/'zzzzzzzz-m7-processing.conf').write_text('[Service]\\nExecStart=\\nExecStart=/home/ec2-user/data-collection-processing/.venv-athena/bin/python -B -m constellation.m7_lifecycle dispatch --unit '+target+'\\nSlice=system.slice\\nMemoryHigh=128M\\nMemoryMax=256M\\nCPUQuota=50%\\nTimeoutStartSec=10min\\nReadWritePaths=/home/ec2-user/data-collection-processing/constellation/autostop\\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
for name in JOBS:
 subprocess.run(['systemctl','restart','--no-block','optima-'+name+'.service'],check=True)
print('Heavy processing controller entrypoints converted to m7 dispatchers')
'''.replace('JOBS',repr(JOBS)))
if __name__=='__main__':main()
