import boto3,json,hashlib
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3',region_name='us-east-1');bucket='data-collection-059416028963-us-east-1-an';base='research-data/constellation-backfill/repairs/2026-11-16-edinet-scope'
decision={'decision_id':'edinet-2016-owner-excluded-2026-11-16','decision_type':'owner_scope_exclusion','source':'edinet_filings','mode':'historical','period_start':'2016-01-01','period_end_exclusive':'2017-01-01','reason':'historical_period_not_required_by_owner','owner_instruction':'The EDINET archive 2016 period is not essential. Please note this and make sure it\u0027s no longer understood as an alert.','recorded_on':'2026-11-16','existing_evidence':'retain','other_years_and_daily_capture':'remain_in_scope'}
body=json.dumps(decision,sort_keys=True).encode();s.put_object(Bucket=bucket,Key=base+'/owner-decision.json',Body=body,ServerSideEncryption='AES256',IfNoneMatch='*');(p/'owner-decision.json').write_bytes(body)
raw=Path('reviewed_source_gaps.py').read_bytes();sha=hashlib.sha256(raw).hexdigest();key=base+'/deployment/'+sha+'/reviewed_source_gaps.py';s.put_object(Bucket=bucket,Key=key,Body=raw,ServerSideEncryption='AES256')
script='''import boto3,hashlib,os,json
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');raw=s.get_object(Bucket=BUCKET,Key=KEY)['Body'].read();assert hashlib.sha256(raw).hexdigest()==SHA;compile(raw,'reviewed_source_gaps.py','exec')
roots=[Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/capture-workers/source'),Path('/opt/constellation/summary-worker'),Path('/opt/constellation/metadata-engine-runtime'),*Path('/opt/constellation/legacy').glob('*')];changed=[]
for root in roots:
 target=root/'reviewed_source_gaps.py'
 if not target.is_file()or target.read_bytes()==raw:continue
 backup=Path('/opt/constellation/tmp/edinet-2016-owner-exclusion-backup')/hashlib.sha256(str(root).encode()).hexdigest()[:12]/'reviewed_source_gaps.py';backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():backup.write_bytes(target.read_bytes())
 temp=target.with_suffix('.owner-scope.tmp');temp.write_bytes(raw);os.chmod(temp,0o644);temp.replace(target);changed.append(str(target))
ns={};exec(compile(raw,'reviewed_source_gaps.py','exec'),ns)
job={'source':'edinet_filings','adapter':'edinet','mode':'historical','start':'2016-12-31','end':'2017-01-01','parameters':{'url':'https://api.edinet-fsa.go.jp/api/v2/documents.json'}}
assert ns['reviewed_gap'](job)['decision_type']=='owner_scope_exclusion'
assert ns['reviewed_gap']({**job,'start':'2017-01-01','end':'2017-01-02'})is None
print(json.dumps({'updated_runtime_files':len(changed),'policy_sha256':SHA,'boundary_checks':'passed'}))
'''.replace('BUCKET',repr(bucket)).replace('KEY',repr(key)).replace('SHA',repr(sha));(p/'deploy_worker.py').write_text(script)
for root in Path('constellation/daily-workspaces').glob('*'):
 target=root/'reviewed_source_gaps.py'
 if not target.is_file():continue
 backup=p/'daily-backups'/root.name/'reviewed_source_gaps.py';backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(target.read_bytes());tmp=target.with_suffix('.owner-scope.tmp');tmp.write_bytes(raw);tmp.replace(target)
(p/'deployment.json').write_text(json.dumps({'key':key,'sha256':sha},indent=2));print('policy and owner decision staged')
