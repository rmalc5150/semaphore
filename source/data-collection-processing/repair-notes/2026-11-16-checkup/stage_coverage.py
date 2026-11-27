import boto3,json
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3');bucket='data-collection-059416028963-us-east-1-an';base='research-data/constellation-backfill/repairs/2026-11-16';s.put_object(Bucket=bucket,Key=base+'/publish.py',Body=(p/'publish_coverage.py').read_bytes(),ServerSideEncryption='AES256')
script='''import boto3,subprocess
from pathlib import Path
p=Path('/opt/constellation/tmp/checkup1116');f=p/'publish.py';f.write_bytes(boto3.client('s3').get_object(Bucket='data-collection-059416028963-us-east-1-an',Key='research-data/constellation-backfill/repairs/2026-11-16/publish.py')['Body'].read())
print(subprocess.run(['systemctl','cat','optima-m7-aux-cms-catalog-publication.service'],capture_output=True,text=True).stdout[-2200:])
r=subprocess.run(['systemd-run','--unit=optima-checkup-1116-coverage-publication','--property=Slice=constellation-workers.slice','--property=MemoryMax=1536M','--property=CPUQuota=50%','--property=RuntimeMaxSec=1200','--property=StandardOutput=append:'+str(p/'publish.log'),'--property=StandardError=append:'+str(p/'publish.log'),'--setenv=AWS_CONFIG_FILE=/dev/null','--setenv=AWS_SHARED_CREDENTIALS_FILE=/dev/null','--setenv=AWS_DEFAULT_REGION=us-east-1','/opt/constellation/legacy-venv/bin/python',str(f)],capture_output=True,text=True);print(r.returncode,r.stdout,r.stderr);assert r.returncode==0
''';(p/'launch_publication.py').write_text(script)
