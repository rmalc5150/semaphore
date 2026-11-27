import boto3,hashlib,os,json
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');raw=s.get_object(Bucket='data-collection-059416028963-us-east-1-an',Key='research-data/constellation-backfill/repairs/2026-11-16-edinet-scope/deployment/95f83408d157c39174c582f57d1f95a3784ab0fad306f1e353277db415282f89/reviewed_source_gaps.py')['Body'].read();assert hashlib.sha256(raw).hexdigest()=='95f83408d157c39174c582f57d1f95a3784ab0fad306f1e353277db415282f89';compile(raw,'reviewed_source_gaps.py','exec')
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
print(json.dumps({'updated_runtime_files':len(changed),'policy_sha256':'95f83408d157c39174c582f57d1f95a3784ab0fad306f1e353277db415282f89','boundary_checks':'passed'}))
