import argparse,base64,hashlib,json,os,subprocess,time
from pathlib import Path
import boto3
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from botocore.config import Config
ROOT=Path('/home/ec2-user/data-collection-processing')
WORK=Path('/tmp/ec2-data-migration-20261020')
BUCKET='data-collection-059416028963-us-east-1-an'
PREFIX='research-data/server-migrations/2026-10-20/ip-172-31-47-178'
S3=boto3.client('s3',region_name='us-east-1',config=Config(retries={'max_attempts':8,'mode':'standard'}))
CODE={'.py','.sh','.sql','.js','.ts','.tsx','.jsx','.css','.toml','.service','.timer','.conf','.slice','.pem','.crt','.key'}
def put_json(key,value):
 body=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
 checksum=base64.b64encode(hashlib.sha256(body).digest()).decode()
 S3.put_object(Bucket=BUCKET,Key=key,Body=body,ContentType='application/json',ServerSideEncryption='AES256',ChecksumSHA256=checksum)
 actual=S3.get_object(Bucket=BUCKET,Key=key)['Body'].read()
 if actual!=body:raise RuntimeError('Receipt readback mismatch')
def snapshot(p):
 s=p.stat();return [s.st_size,s.st_mtime_ns,s.st_ino,s.st_dev]
def select(group):
 if group not in {'root-data','reference-data'} and (Path(group).name != group or not (ROOT/group).is_dir()):
  raise ValueError('Expected a single existing data directory name')
 if group=='reference-data':
  candidates=[]
  for pattern in ('company-universe.v*.json','company-id-registry*.json','company-admission-ledger*.json','bls-release-vintages.json','bls-release-bootstrap.json','source-schedule-inventory.json'):
   candidates.extend((ROOT/'config').glob(pattern))
  candidates.extend(ROOT.glob('patent_pilot_companies.json'))
 elif group=='root-data':
  candidates=[p for p in ROOT.iterdir() if p.is_file() and (p.suffix in {'.sqlite3','.db','.jsonl'} or p.name in {'china-verification-status.json','.uspto-request-gate.json'} or p.name.endswith(('.sqlite3-wal','.sqlite3-shm','.sqlite3-journal')))]
 else:candidates=[p for p in (ROOT/group).rglob('*') if p.is_file()]
 out={}
 for p in candidates:
  if p.is_symlink() or p.suffix in CODE or p.name in {'README.md','SKILL.md','AGENTS.md'}:continue
  if '__pycache__' in p.parts:continue
  out[str(p.relative_to(ROOT))]=snapshot(p)
 return out

def migrate(group,delete,compress=False):
 WORK.mkdir(parents=True,exist_ok=True)
 files=select(group)
 if group in {'config','schemas','tests','examples','systemd'} or group.startswith('.'):
  raise ValueError('Refusing to migrate configuration, code, fixtures, or hidden directories')
 if not files:print('EMPTY',group,flush=True);return
 total=sum(s[0] for s in files.values());label=group.replace('/','_')
 print('START',group,'files',len(files),'bytes',total,flush=True)
 listpath=WORK/(label+'.files');listpath.write_bytes(b''.join(os.fsencode(p)+b'\0' for p in sorted(files)))
 key=PREFIX+'/'+label+('.tar.gz' if compress else '.tar')
 try:
  S3.head_object(Bucket=BUCKET,Key=key)
 except Exception as exc:
  if getattr(exc,'response',{}).get('Error',{}).get('Code') not in {'404','NoSuchKey','NotFound'}:raise
 else:raise ValueError('Archive already exists; use a new migration prefix to preserve the earlier backup')
 put_json(PREFIX+'/'+label+'.inventory.json',{'root':str(ROOT),'group':group,'files':files,'data_bytes':total,'archive_key':key,'preserved_source_extensions':sorted(CODE)})
 upload=S3.create_multipart_upload(Bucket=BUCKET,Key=key,ContentType=('application/gzip' if compress else 'application/x-tar'),ServerSideEncryption='AES256',ChecksumAlgorithm='SHA256',Metadata={'source-root':str(ROOT),'group':group})
 uid=upload['UploadId'];parts=[];digest=hashlib.sha256();nbytes=0
 with (WORK/(label+'.tar.stderr')).open('wb') as err:
  proc=subprocess.Popen(['tar',*(['--use-compress-program=gzip -1'] if compress else []),'-c','-f','-','--no-recursion','--null','--verbatim-files-from','-T',str(listpath)],cwd=ROOT,stdout=subprocess.PIPE,stderr=err)
  try:
   def send_part(number,chunk):
    result=S3.upload_part(Bucket=BUCKET,Key=key,UploadId=uid,PartNumber=number,Body=chunk,ChecksumSHA256=base64.b64encode(hashlib.sha256(chunk).digest()).decode())
    return {'PartNumber':number,'ETag':result['ETag'],'ChecksumSHA256':result['ChecksumSHA256']}
   pending=deque();part=0
   with ThreadPoolExecutor(max_workers=3) as pool:
    while True:
     data=proc.stdout.read(32*1024*1024)
     if not data:break
     digest.update(data);nbytes+=len(data);part+=1
     if len(pending)>=3:parts.append(pending.popleft().result())
     pending.append(pool.submit(send_part,part,data))
     if part%16==0:print('UPLOADED',group,nbytes,flush=True)
    while pending:parts.append(pending.popleft().result())
   if proc.wait()!=0:raise RuntimeError('tar failed: '+(WORK/(label+'.tar.stderr')).read_text()[:2000])
   S3.complete_multipart_upload(Bucket=BUCKET,Key=key,UploadId=uid,MultipartUpload={'Parts':parts})
  except BaseException:
   proc.kill();proc.wait();S3.abort_multipart_upload(Bucket=BUCKET,Key=key,UploadId=uid);raise
  finally:
   proc.stdout.close()
 response=S3.get_object(Bucket=BUCKET,Key=key);remote=hashlib.sha256();read_bytes=0
 try:
  for chunk in response['Body'].iter_chunks(chunk_size=8*1024*1024):remote.update(chunk);read_bytes+=len(chunk)
 finally:response['Body'].close()
 if read_bytes!=nbytes or remote.digest()!=digest.digest():raise RuntimeError('Full archive SHA256 readback mismatch')
 changed=[p for p,s in files.items() if not (ROOT/p).exists() or snapshot(ROOT/p)!=s]
 receipt={'group':group,'archive_uri':'s3://'+BUCKET+'/'+key,'archive_bytes':nbytes,'archive_sha256':digest.hexdigest(),'file_count':len(files),'data_bytes':total,'full_s3_readback_verified':True,'changed_files':changed,'verified_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 put_json(PREFIX+'/'+label+'.verified.json',receipt)
 deleted=freed=0
 if delete:
  for p,s in files.items():
   q=ROOT/p
   if q.exists() and not q.is_symlink() and snapshot(q)==s:q.unlink();deleted+=1;freed+=s[0]
 receipt.update(deleted_files=deleted,deleted_bytes=freed)
 put_json(PREFIX+'/'+label+'.result.json',receipt)
 (WORK/(label+'.result.json')).write_text(json.dumps(receipt,indent=2))
 print('DONE',json.dumps(receipt),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('groups',nargs='+');p.add_argument('--delete-verified',action='store_true');p.add_argument('--gzip',action='store_true');a=p.parse_args()
 for group in a.groups:migrate(group,a.delete_verified,a.gzip)
