import json,hashlib
from pathlib import Path
from ops import remote,M7,session,B,BASE,P
files={}
for name in ['metadata_engine/economic_records.py','metadata_engine/evidence.py','metadata_engine/labelling.py','metadata_engine/source_policies.py','reviewed_metadata_publication.py','epo_ops.py',str(P/'validate_economic.py')]:
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key='research-data/constellation-backfill/deployments/entries-62-75-20261114/'+sha+'/'+Path(name).name
 session.client('s3').put_object(Bucket=B,Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
policies=json.loads((P/'policies.json').read_text());session.client('s3').put_object(Bucket=B,Key=BASE+'policies.json',Body=(P/'policies.json').read_bytes(),ServerSideEncryption='AES256')
code='''import json,boto3,hashlib,os,subprocess,time
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');files=FILES;policies=POLICIES
roots=[Path('/opt/constellation/metadata-engine-runtime'),Path('/opt/constellation/auxiliary-publication/source')]
for name,ref in files.items():
 raw=s.get_object(Bucket=BUCKET,Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];compile(raw,name,'exec')
 relative=name if name.startswith('metadata_engine/')or'/'not in name else'validate_economic_6275.py'
 for root in roots:
  p=root/relative;backup=Path('/opt/constellation/tmp/entries-62-75-backup')/root.name/relative
  if p.exists()and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(p.read_bytes())
  tmp=p.with_suffix('.repair.tmp');tmp.write_bytes(raw);os.chmod(tmp,0o644);os.chown(tmp,1000,1000);tmp.replace(p)
for root in roots:
 p=root/'config/metadata-engine.json';cfg=json.loads(p.read_text())
 for source,policy in policies.items():cfg['contracts'][source]=policy;cfg.setdefault('verified_source_failure_handling',{})[source]='queue_by_source_date'
 cfg['build_sha256']=hashlib.sha256(b''.join(x.read_bytes()for x in sorted((root/'metadata_engine').glob('*.py')))).hexdigest();tmp=p.with_suffix('.repair.tmp');tmp.write_text(json.dumps(cfg,indent=2)+'\\n');os.chown(tmp,1000,1000);os.chmod(tmp,0o644);tmp.replace(p)
subprocess.run(['systemd-run','--unit=optima-entries-6275-validate-20261114','--no-block','--collect','-p','User=ec2-user','-p','WorkingDirectory=/opt/constellation/metadata-engine-runtime','-p','Slice=constellation-workers.slice','-p','MemoryMax=768M','-p','CPUQuota=25%','-p','RuntimeMaxSec=900','/opt/constellation/legacy-venv/bin/python','-B','validate_economic_6275.py'],check=True)
print(json.dumps({'files':files,'installed_at_epoch':time.time()}))
'''.replace('FILES',repr(files)).replace('POLICIES',repr(policies)).replace('BUCKET',repr(B))
r=remote(M7,code);(P/'economic-deployment.json').write_text(r['out']+'\n');print('Economic adapters deployed; original validation running on m7.')
