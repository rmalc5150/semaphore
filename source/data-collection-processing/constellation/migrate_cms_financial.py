"""Move bounded CMS financial parsing and readback to the shared worker."""
import json
from constellation.finish_aux_migration import remote,T3,M7,ROOT,session

def main():
 bucket='data-collection-059416028963-us-east-1-an';arn='arn:aws:s3:::'+bucket
 policy={'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':['s3:GetObject','s3:PutObject'],'Resource':arn+'/research-data/cms-financial/*'},{'Effect':'Allow','Action':'s3:ListBucket','Resource':arn,'Condition':{'StringLike':{'s3:prefix':['research-data/cms-financial/*']}}}]}
 iam=session.client('iam');role='constellation-backfill-worker'
 try:iam.put_role_policy(RoleName=role,PolicyName='M7CMSFinancialScope',PolicyDocument=json.dumps(policy))
 except iam.exceptions.LimitExceededException:
  # Statement identifiers are optional labels, not permissions. Preserve every grant/condition.
  before={name:iam.get_role_policy(RoleName=role,PolicyName=name)['PolicyDocument']for name in iam.list_role_policies(RoleName=role)['PolicyNames']}
  backup=ROOT/'constellation/migration/iam-inline-before-label-compaction.json';backup.write_text(json.dumps(before,indent=2));backup.chmod(0o600)
  for name,document in before.items():
   if not any('Sid'in statement for statement in document['Statement']):continue
   compact={**document,'Statement':[{k:v for k,v in statement.items()if k!='Sid'}for statement in document['Statement']]}
   iam.put_role_policy(RoleName=role,PolicyName=name,PolicyDocument=json.dumps(compact,separators=(',',':')))
  iam.put_role_policy(RoleName=role,PolicyName='M7CMSFinancialScope',PolicyDocument=json.dumps(policy,separators=(',',':')))
  print('Removed optional IAM statement labels; existing permissions unchanged',flush=True)
 remote(T3,"import subprocess;subprocess.run(['systemctl','stop','optima-cms-financial-resumed.timer','optima-cms-financial-resumed.service'],check=True);print('CMS controller paused at checkpoint handoff')")
 remote(M7,'''from pathlib import Path
import boto3,json,hashlib,sqlite3,subprocess,os
root=Path('/opt/constellation/auxiliary-publication/source');s=boto3.client('s3',region_name='us-east-1');bucket=__BUCKET__
ref=json.loads(s.get_object(Bucket=bucket,Key='research-data/constellation-backfill/cms-payments/registry/latest.json')['Body'].read());body=s.get_object(Bucket=bucket,Key='research-data/'+ref['key'])['Body'].read();assert hashlib.sha256(body).hexdigest()==ref['sha256']
state=Path('/opt/constellation/state/cms-financial');state.mkdir(parents=True,exist_ok=True);os.chown(state,1000,1000);db=state/'registry.sqlite3'
tmp=state/'registry.incoming.sqlite3';tmp.write_bytes(body)
with sqlite3.connect(tmp)as c:
 assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 count=c.execute("SELECT count(*) FROM editions WHERE status='done'").fetchone()[0];assert count>=20
if db.exists():
 with sqlite3.connect(db)as c:existing=c.execute("SELECT count(*) FROM editions WHERE status='done'").fetchone()[0]
 if existing<count:db.rename(state/'registry.before-migration.sqlite3');tmp.replace(db)
 else:tmp.unlink()
else:tmp.replace(db)
os.chown(db,1000,1000)
cfg=json.loads((root/'config/cms-financial-resumed.json').read_text());cfg.update(state_file=str(db),notify_on_completion=False,status_file=str(root/'reports/cms-financial-backfill-latest.json'))
(root/'config/cms-financial-m7.json').write_text(json.dumps(cfg,indent=2));os.chown(root/'config/cms-financial-m7.json',1000,1000)
unit='[Unit]\\nDescription=CMS financial parsing and Athena verification on m7\\nAfter=network-online.target\\n[Service]\\nType=oneshot\\nUser=ec2-user\\nWorkingDirectory='+str(root)+'\\nExecStart=/opt/constellation/legacy-venv/bin/python -B cms_payments_resumed.py --mode financial --config config/cms-financial-m7.json\\nSlice=constellation-workers.slice\\nMemoryHigh=1G\\nMemoryMax=2G\\nMemorySwapMax=0\\nCPUQuota=100%\\nTimeoutStartSec=30min\\nEnvironment=AWS_DEFAULT_REGION=us-east-1\\nEnvironment=ARROW_NUM_THREADS=1\\n'
Path('/etc/systemd/system/optima-m7-cms-financial-resumed.service').write_text(unit)
subprocess.run(['systemctl','daemon-reload'],check=True);subprocess.run(['systemctl','start','--no-block','optima-m7-cms-financial-resumed.service'],check=True)
print(json.dumps({'done_editions_preserved':count,'checkpoint_verified':True,'worker_started':True}))
'''.replace('__BUCKET__',repr(bucket)))
 remote(T3,'''from pathlib import Path
import subprocess
p=Path('/etc/systemd/system/optima-cms-financial-resumed.service.d');p.mkdir(exist_ok=True)
(p/'zzzzzzzz-m7-processing.conf').write_text('[Service]\\nExecStart=\\nExecStart=/home/ec2-user/data-collection-processing/.venv-athena/bin/python -B -m constellation.m7_lifecycle dispatch --unit optima-m7-cms-financial-resumed.service\\nSlice=system.slice\\nMemoryHigh=128M\\nMemoryMax=256M\\nCPUQuota=50%\\nTimeoutStartSec=10min\\n')
subprocess.run(['systemctl','daemon-reload'],check=True);subprocess.run(['systemctl','start','optima-cms-financial-resumed.timer'],check=True)
print('CMS financial timer now dispatches m7 processing')
''')

if __name__=='__main__':main()
