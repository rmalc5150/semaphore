"""Narrow worker patches; run via SSM on the next scheduled boot."""
import os,json,hashlib
from pathlib import Path
import boto3
results=[]
def change(target, replacements):
 if not target.is_file():return
 old=target.read_text();new=old
 for before,after,count in replacements:
  if before not in new:
   if after in new:continue
   raise RuntimeError('Expected deployment anchor missing: '+str(target))
  if new.count(before)!=count:raise RuntimeError('Unexpected deployment anchor count: '+str(target))
  new=new.replace(before,after)
 compile(new,str(target),'exec')
 if new!=old:
  backup=Path('/opt/constellation/tmp/checkup1120-backup')/hashlib.sha256(str(target).encode()).hexdigest()[:12]/target.name;backup.parent.mkdir(parents=True,exist_ok=True)
  if not backup.exists():backup.write_text(old)
  temporary=target.with_suffix('.1120.tmp');temporary.write_text(new);st=target.stat();os.chmod(temporary,st.st_mode & 0o777);os.chown(temporary,st.st_uid,st.st_gid);temporary.replace(target)
 results.append({'path':str(target),'status':'installed'if new!=old else'already_installed','sha256':hashlib.sha256(new.encode()).hexdigest()})
for root in [Path('/opt/constellation/research-publication/source'),Path('/opt/constellation/auxiliary-publication/source')]:
 change(root/'window_publication.py',[("scan_key = 'operations/'+owner+'/publication-scan.json'","scan_key = 'operations/'+owner+'/publication-retries/_scan-cursor.json'",1)])
for root in [Path('/opt/constellation/capture-workers/source')]:
 change(root/'patent_collection.py',[('upper - lower > timedelta(minutes=5)','upper - lower > timedelta(seconds=1)',2)])
assert any('research-publication/source/window_publication.py'in r['path']for r in results)
assert any('capture-workers/source/patent_collection.py'in r['path']for r in results)
s=boto3.client('s3');bucket='data-collection-059416028963-us-east-1-an'
# Verify a real conditional metadata read/write under the already permitted path.
key='research-data/operations/regulatory/publication-retries/_scan-cursor-permission-probe-20261120.json'
try:
 s.put_object(Bucket=bucket,Key=key,Body=json.dumps({'kind':'permission_probe','not_a_publication_receipt':True}).encode(),IfNoneMatch='*',ServerSideEncryption='AES256')
except s.exceptions.ClientError as e:
 if e.response['Error']['Code']not in ('PreconditionFailed','412'):raise
assert json.loads(s.get_object(Bucket=bucket,Key=key)['Body'].read())['not_a_publication_receipt']is True
result={'files':results,'cursor_permission_probe':'passed'}
s.put_object(Bucket=bucket,Key='research-data/constellation-backfill/repairs/2026-11-20/deployment-result.json',Body=json.dumps(result).encode(),ServerSideEncryption='AES256')
print(json.dumps(result))
