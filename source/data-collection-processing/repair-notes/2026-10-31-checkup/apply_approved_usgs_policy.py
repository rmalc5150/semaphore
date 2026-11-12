import json
from pathlib import Path
import boto3
p=Path(__file__).parent;i=boto3.client('iam',region_name='us-east-1');role='constellation-backfill-worker';name='constellation-legacy-artifacts'
before=json.loads((p/'artifact-policy-before.json').read_text());approved=json.loads((p/'artifact-policy-proposed.json').read_text())
assert approved['Statement'][:-1]==before['Statement']
assert approved['Statement'][-1]=={'Sid':'USGSEnrichmentArtifacts','Effect':'Allow','Action':['s3:GetObject','s3:PutObject'],'Resource':['arn:aws:s3:::data-collection-059416028963-us-east-1-an/research-data/operations/usgs-minerals/'+s+'/*'for s in ('directories','report-heads','reports')]}
current=i.get_role_policy(RoleName=role,PolicyName=name)['PolicyDocument']
if current!=approved:
 assert current==before,'Policy changed since proposal; refusing to overwrite newer changes'
 i.put_role_policy(RoleName=role,PolicyName=name,PolicyDocument=json.dumps(approved))
actual=i.get_role_policy(RoleName=role,PolicyName=name)['PolicyDocument'];assert actual==approved
(p/'artifact-policy-applied.json').write_text(json.dumps(actual,indent=2));print('Exact approved policy applied and read-back verified; all previous statements preserved')
