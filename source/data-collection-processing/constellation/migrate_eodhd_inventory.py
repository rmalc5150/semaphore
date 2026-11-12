"""Move EODHD inventory execution; let any current controller checkpoint finish."""
import json
from constellation.finish_aux_migration import remote,T3,M7,ROOT,session

def main():
 iam=session.client('iam');role='constellation-backfill-worker'
 name='constellation-specific-historical-sources';policy=iam.get_role_policy(RoleName=role,PolicyName=name)['PolicyDocument']
 resource=json.loads((ROOT/'config/eodhd-universe.json').read_text())['secret_id']
 for stmt in policy['Statement']:
  if stmt['Action']=='secretsmanager:GetSecretValue':
   if resource not in stmt['Resource']:stmt['Resource'].append(resource)
 iam.put_role_policy(RoleName=role,PolicyName=name,PolicyDocument=json.dumps(policy,separators=(',',':')))
 name='M7DailyStreamProgress';policy=iam.get_role_policy(RoleName=role,PolicyName=name)['PolicyDocument'];resource='arn:aws:s3:::data-collection-059416028963-us-east-1-an/research-data/operations/eodhd/*'
 for stmt in policy['Statement']:
  if 's3:PutObject'in stmt['Action']:
   if resource not in stmt['Resource']:stmt['Resource'].append(resource)
 iam.put_role_policy(RoleName=role,PolicyName=name,PolicyDocument=json.dumps(policy,separators=(',',':')))
 remote(M7,'''from pathlib import Path
import subprocess,os
root=Path('/opt/constellation/auxiliary-publication/source')
for name in ('eodhd_inventory_daily.py','eodhd_universe.py','schemas/research-data.schema.json','config/company-universe.v0.1.json','config/eodhd-universe.json'):assert (root/name).is_file(),name
unit='[Unit]\\nDescription=EODHD global inventory on m7\\nAfter=network-online.target\\n[Service]\\nType=oneshot\\nUser=ec2-user\\nWorkingDirectory='+str(root)+'\\nExecStart=/opt/constellation/legacy-venv/bin/python -B eodhd_inventory_daily.py\\nSlice=constellation-workers.slice\\nMemoryHigh=1G\\nMemoryMax=2G\\nMemorySwapMax=0\\nCPUQuota=100%\\nTimeoutStartSec=45min\\nSuccessExitStatus=2\\nEnvironment=AWS_DEFAULT_REGION=us-east-1\\nEnvironment=CONSTELLATION_SHARED_HTTP_LIMITS=1\\nEnvironment=CONSTELLATION_ROLE=worker\\n'
Path('/etc/systemd/system/optima-m7-eodhd-inventory.service').write_text(unit);subprocess.run(['systemctl','daemon-reload'],check=True)
print('m7 EODHD inventory installed; current t3 checkpoint is allowed to finish')
''')
 remote(T3,'''from pathlib import Path
import subprocess,json
p=Path('/etc/systemd/system/optima-eodhd-inventory.service.d');p.mkdir(exist_ok=True)
(p/'zzzzzzzz-m7-processing.conf').write_text('[Service]\\nExecStart=\\nExecStart=/home/ec2-user/data-collection-processing/.venv-athena/bin/python -B -m constellation.m7_lifecycle dispatch --unit optima-m7-eodhd-inventory.service\\nSlice=system.slice\\nMemoryHigh=128M\\nMemoryMax=256M\\nCPUQuota=50%\\nTimeoutStartSec=10min\\nReadWritePaths=/home/ec2-user/data-collection-processing/constellation/autostop\\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
state=subprocess.check_output(['systemctl','show','optima-eodhd-inventory.service','-p','ActiveState','--value'],text=True).strip()
if state not in ('active','activating','deactivating'):subprocess.run(['systemctl','start','--no-block','optima-eodhd-inventory.service'],check=True)
print(json.dumps({'next_inventory_execution':'m7','current_controller_state':state,'current_checkpoint_preserved':True}))
''')

if __name__=='__main__':main()
