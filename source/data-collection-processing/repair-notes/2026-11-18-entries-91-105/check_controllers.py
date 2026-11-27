from ops import *
code=r'''import json,subprocess,boto3,datetime
from pathlib import Path
prefixes=('constellation-public-daily','constellation-public-api-daily','optima-metadata-engine','optima-m7','constellation-historical','optima-historical')
raw=subprocess.check_output(['systemctl','list-units','--all','--type=service','--type=timer','--no-legend','--plain','--no-pager'],text=True)
units=[]
for line in raw.splitlines():
 parts=line.split()
 if parts and any(parts[0].startswith(p)for p in prefixes):units.append(parts[0])
def show(unit):
 body=subprocess.check_output(['systemctl','show',unit,'--property=Id,ActiveState,SubState,Result,ExecMainStatus,NextElapseUSecRealtime,NextElapseUSecMonotonic,LastTriggerUSec'],text=True)
 return dict(line.split('=',1)for line in body.splitlines()if '='in line)
out={'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'units':[show(u)for u in sorted(set(units))],'batch_policy':json.loads(Path('config/m7-batch-policy.json').read_text())}
state=json.loads(Path('constellation/autostop/m7-batch.json').read_text());out['batch_state']={k:state.get(k)for k in ('phase','stopped_at','started_at','reason')}
ec2=boto3.client('ec2',region_name='us-east-1');r=ec2.describe_instances(InstanceIds=['i-06241bd1c4e91c2fc'])['Reservations'][0]['Instances'][0];out['worker']={'id':r['InstanceId'],'type':r['InstanceType'],'state':r['State']['Name']}
s=boto3.client('s3',region_name='us-east-1');s.put_object(Bucket=BUCKET,Key=BASE+'controller-check.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print(json.dumps({'worker':out['worker'],'units':out['units']}))
'''.replace('BUCKET',repr(B)).replace('BASE',repr(BASE))
r=remote(T3,code);(P/'controller-check-response.json').write_text(r['out']);raw=session.client('s3').get_object(Bucket=B,Key=BASE+'controller-check.json')['Body'].read();(P/'controller-check.json').write_bytes(raw);data=json.loads(raw);print('Worker:',data['worker']);print('Controller units:',len(data['units']));print('Failed:',[(u['Id'],u.get('Result'))for u in data['units']if u.get('ActiveState')=='failed'])
