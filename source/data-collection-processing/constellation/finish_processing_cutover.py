"""Deploy worker-only metadata publication and shared daily-provider admission."""
import io,tarfile,json,hashlib
from constellation.finish_aux_migration import remote,M7,T3,ROOT,session

def main():
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w:gz')as tar:
        for name in ('m7_metadata_publication.py','metadata_engine/controller.py','metadata_engine/runtime_db.py','constellation/__init__.py','constellation/control.py','constellation/shared_limits.py'):
            tar.add(ROOT/name,arcname=name)
        cfg=json.loads((ROOT/'config/constellation-infrastructure.json').read_text());cfg.pop('controller_secret_arn',None)
        raw=json.dumps(cfg).encode();info=tarfile.TarInfo('config/constellation-infrastructure.json');info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
    body=buf.getvalue();sha=hashlib.sha256(body).hexdigest();key='research-data/constellation-backfill/deployments/processing-hotfix-'+sha+'.tgz';s=session.client('s3');bucket='data-collection-059416028963-us-east-1-an';s.put_object(Bucket=bucket,Key=key,Body=body,ServerSideEncryption='AES256')
    remote(M7,'''from pathlib import Path
import boto3,hashlib,tarfile,io,os,subprocess
root=Path('/opt/constellation/auxiliary-publication/source');body=boto3.client('s3',region_name='us-east-1').get_object(Bucket=BUCKET,Key=KEY)['Body'].read();assert hashlib.sha256(body).hexdigest()==SHA
with tarfile.open(fileobj=io.BytesIO(body),mode='r:gz')as tar:
 for member in tar.getmembers():
  target=root/member.name;target.parent.mkdir(parents=True,exist_ok=True);tmp=target.with_suffix('.hotfix');tmp.write_bytes(tar.extractfile(member).read());os.chown(tmp,1000,1000);tmp.replace(target)
unit='[Unit]\\nDescription=Metadata publication on m7\\n[Service]\\nType=oneshot\\nUser=ec2-user\\nWorkingDirectory='+str(root)+'\\nExecStart=/usr/bin/flock /opt/constellation/auxiliary-publication/publish.lock /opt/constellation/legacy-venv/bin/python -B m7_metadata_publication.py\\nSlice=constellation-workers.slice\\nMemoryMax=768M\\nCPUQuota=100%\\nTimeoutStartSec=30min\\nEnvironment=AWS_DEFAULT_REGION=us-east-1\\n'
Path('/etc/systemd/system/optima-m7-aux-metadata-publication.service').write_text(unit)
p=Path('/etc/systemd/system/optima-m7-aux-collection-daily.service.d');p.mkdir(exist_ok=True)
(p/'50-shared-provider-gates.conf').write_text('[Service]\\nEnvironment=CONSTELLATION_SHARED_HTTP_LIMITS=1\\nEnvironment=CONSTELLATION_ROLE=worker\\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
for name in ('collection-daily','specialist-publication','metadata-publication'):
 subprocess.run(['systemctl','restart','--no-block','optima-m7-aux-'+name+'.service'],check=True)
print('m7 metadata publication and shared daily-source gates enabled')
'''.replace('BUCKET',repr(bucket)).replace('KEY',repr(key)).replace('==SHA','=='+repr(sha)))
    remote(T3,'''from pathlib import Path
import subprocess
for unit in ('optima-fda-product-codes-capture.service','optima-patents-reviewed-google.service','optima-patents-reviewed-odp.service'):
 folder=Path('/etc/systemd/system/'+unit+'.d');folder.mkdir(exist_ok=True)
 (folder/'zzzz-bounded-capture-runtime.conf').write_text('[Service]\\nTimeoutStartSec=12min\\nCPUQuota=50%\\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
for unit in ('optima-fda-product-codes-capture.service','optima-patents-reviewed-google.service','optima-patents-reviewed-odp.service'):
 state=subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','--value'],text=True).strip()
 if state in ('failed','inactive'):subprocess.run(['systemctl','start','--no-block',unit],check=True)
print('Retained bounded capture on t3; fixed systemd timeout overruns')
''')
if __name__=='__main__':main()
