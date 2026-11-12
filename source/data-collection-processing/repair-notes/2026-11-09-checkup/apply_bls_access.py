"""Prepared narrow IAM repair; run after explicit owner approval."""
import json,boto3
from pathlib import Path
p=Path(__file__).parent;i=boto3.client('iam',region_name='us-east-1');role='constellation-backfill-worker';name='constellation-legacy-artifacts'
before=json.loads((p/'bls-policy-before.json').read_text());after=json.loads((p/'bls-policy-proposed.json').read_text())
assert after['Statement'][:-1]==before['Statement']
assert after['Statement'][-1]=={'Sid':'BLSLaborEnrichmentArtifacts','Effect':'Allow','Action':['s3:GetObject','s3:PutObject'],'Resource':['arn:aws:s3:::data-collection-059416028963-us-east-1-an/research-data/operations/bls-labor/'+v+'/*'for v in ['joins-cache','observed','versions']]}
assert i.get_role_policy(RoleName=role,PolicyName=name)['PolicyDocument']==before,'Policy changed; stop rather than overwrite'
i.put_role_policy(RoleName=role,PolicyName=name,PolicyDocument=json.dumps(after))
actual=i.get_role_policy(RoleName=role,PolicyName=name)['PolicyDocument'];assert actual==after
(p/'bls-policy-applied.json').write_text(json.dumps(actual,indent=2));print('BLS metadata access applied; no delete permission or existing statement changed')
