"""Restore authoritative publication configs and repair bounded gap audit runtime."""
import boto3,hashlib,io,tarfile,json
from constellation.finish_aux_migration import remote,M7,T3

def main():
 s=boto3.client('s3',region_name='us-east-1');bucket='data-collection-059416028963-us-east-1-an'
 head=json.loads(s.get_object(Bucket=bucket,Key='research-data/operations/s3-runtime/current.json')['Body'].read())
 buf=io.BytesIO();names=[]
 with tarfile.open(fileobj=buf,mode='w:gz')as tar:
  for name,entry in head['paths'].items():
   if not name.startswith('config/')or not name.endswith('.json'):continue
   if not ('universe' in name or 'taxonomy' in name):continue
   body=s.get_object(Bucket=bucket,Key=entry['key'])['Body'].read();assert hashlib.sha256(body).hexdigest()==entry['sha256']
   info=tarfile.TarInfo(name);info.size=len(body);tar.addfile(info,io.BytesIO(body));names.append(name)
 raw=buf.getvalue();sha=hashlib.sha256(raw).hexdigest();key='research-data/constellation-backfill/deployments/authoritative-config-'+sha+'.tgz';s.put_object(Bucket=bucket,Key=key,Body=raw,ServerSideEncryption='AES256')
 remote(M7,'''import boto3,io,tarfile,hashlib,os,subprocess
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');body=s.get_object(Bucket=BUCKET,Key=KEY)['Body'].read();assert hashlib.sha256(body).hexdigest()==SHA
root=Path('/opt/constellation/auxiliary-publication/source')
with tarfile.open(fileobj=io.BytesIO(body),mode='r:gz')as tar:
 for member in tar.getmembers():
  assert member.isfile() and member.name in NAMES
  target=root/member.name;target.parent.mkdir(parents=True,exist_ok=True)
  temp=target.with_suffix('.restored');temp.write_bytes(tar.extractfile(member).read());os.chown(temp,1000,1000);temp.replace(target)
for name in NAMES:os.chown(root/name,1000,1000)
print('Restored authoritative configs:',NAMES)
print('Bucket location:',s.get_bucket_location(Bucket=BUCKET).get('LocationConstraint'))
for name in ('specialist-publication','cms-coverage-publication','news-publication'):
 subprocess.run(['systemctl','restart','--no-block','optima-m7-aux-'+name+'.service'],check=True)
'''.replace('BUCKET',repr(bucket)).replace('KEY',repr(key)).replace('SHA',repr(sha)).replace('NAMES',repr(names)))
 remote(T3,'''from pathlib import Path
import subprocess
p=Path('/etc/systemd/system/constellation-gap-audit.service.d');p.mkdir(exist_ok=True)
(p/'50-bounded-audit.conf').write_text('[Service]\\nTimeoutStartSec=20min\\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','restart','--no-block','constellation-gap-audit.service'],check=True)
print('Gap audit skips successful raw jobs and has a bounded 20-minute timeout')
''')
if __name__=='__main__':main()
