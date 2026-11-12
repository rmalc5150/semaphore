import json,boto3
from pathlib import Path
p=Path(__file__).parent;i=boto3.client('iam',region_name='us-east-1');role='constellation-backfill-worker';name='constellation-legacy-artifacts'
before=i.get_role_policy(RoleName=role,PolicyName=name)['PolicyDocument'];(p/'bls-policy-before.json').write_text(json.dumps(before,indent=2))
statement={'Sid':'BLSLaborEnrichmentArtifacts','Effect':'Allow','Action':['s3:GetObject','s3:PutObject'],'Resource':['arn:aws:s3:::data-collection-059416028963-us-east-1-an/research-data/operations/bls-labor/'+v+'/*' for v in ['joins-cache','observed','versions']]}
assert not any(x.get('Sid')==statement['Sid'] for x in before['Statement'])
after={**before,'Statement':before['Statement']+[statement]};(p/'bls-policy-proposed.json').write_text(json.dumps(after,indent=2))
r=i.simulate_principal_policy(PolicySourceArn='arn:aws:iam::059416028963:role/'+role,ActionNames=['s3:GetObject','s3:PutObject'],ResourceArns=[x[:-1]+'review-test.json' for x in statement['Resource']]);out=[{'action':v['EvalActionName'],'resource':v['EvalResourceName'],'decision':v['EvalDecision']}for v in r['EvaluationResults']];(p/'bls-permission-simulation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
