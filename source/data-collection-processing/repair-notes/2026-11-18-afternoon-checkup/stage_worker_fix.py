import json,base64,boto3
from pathlib import Path
p=Path(__file__).parent
# Surgical anchors preserve other worker-specific edits and fail closed on drift.
changes=[
('    blocked_commits = 0\n','    blocked_commits = 0\n    scan_key = \'operations/\'+owner+\'/publication-scan.json\'\n    scan_token = None\n    scan_last = None\n    bounded_scan = owner == \'regulatory\' and window_ids is None\n'),
('        keys = list_keys(store,settings,prefix)\n        with ThreadPoolExecutor(max_workers=8) as pool:', '''        keys = list_keys(store,settings,prefix)
        if bounded_scan:
            scan, scan_token = load_stored(store, scan_key)
            after = (scan or {}).get('last_key', '')
            keys = ([k for k in keys if k > after] + [k for k in keys if k <= after])[:128]
        with ThreadPoolExecutor(max_workers=4 if bounded_scan else 8) as pool:'''),
("        ordered = sorted(queued,key=lambda row:(row.get('queued_at',''),row['window_id']))\n        with ThreadPoolExecutor(max_workers=8) as pool:","        ordered = queued if bounded_scan else sorted(queued,key=lambda row:(row.get('queued_at',''),row['window_id']))\n        with ThreadPoolExecutor(max_workers=4 if bounded_scan else 8) as pool:"),
('            if done:\n                continue',"            if done:\n                if bounded_scan: scan_last = prefix+item['window_id']+'.json'\n                continue"),
("            if retry and retry.get('source_hash')==source_hash and retry['retry_after']>now():\n                continue", "            if retry and retry.get('source_hash')==source_hash and retry['retry_after']>now():\n                if bounded_scan: scan_last = prefix+item['window_id']+'.json'\n                continue"),
("                outcomes.append(failure)\n    return {'status':", "                outcomes.append(failure)\n            if bounded_scan: scan_last = prefix+item['window_id']+'.json'\n    if scan_last:\n        write_json(store,scan_key,{'last_key':scan_last,'checked_at':now(),'max_candidates':128},scan_token)\n    return {'status':")]
# Compare staged code to the tested module, ignoring comments only.
import ast
tested=Path('window_publication.py').read_text()
original='\n'.join(line for line in tested.split('\n') if not line.lstrip().startswith('#'))
for before,after in reversed(changes):
 assert after in original, 'preflight reverse anchor'
 original=original.replace(after,before,1)
transformed=original
for before,after in changes:
 assert transformed.count(before)==1, 'preflight forward anchor'
 transformed=transformed.replace(before,after,1)
assert ast.dump(ast.parse(transformed))==ast.dump(ast.parse(tested)), 'staged code differs from tested code'
script='''import os,json,hashlib
from pathlib import Path
import boto3
changes=CHANGES
results=[]
for root in [Path('/opt/constellation/research-publication/source'),Path('/opt/constellation/auxiliary-publication/source')]:
 target=root/'window_publication.py'
 if not target.exists():continue
 old=target.read_text()
 if "bounded_scan = owner == 'regulatory'" in old:
  results.append({'root':str(root),'status':'already_installed'});continue
 new=old
 for before,after in changes:
  if new.count(before)!=1:raise RuntimeError('Deployment anchor differs: '+str(root))
  new=new.replace(before,after,1)
 compile(new,str(target),'exec');backup=Path('/opt/constellation/tmp/checkup1118-afternoon-backup')/hashlib.sha256(str(root).encode()).hexdigest()[:12]/target.name;backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():backup.write_text(old)
 temp=target.with_suffix('.1118afternoon.tmp');temp.write_text(new);st=target.stat();os.chmod(temp,st.st_mode & 0o777);os.chown(temp,st.st_uid,st.st_gid);temp.replace(target)
 results.append({'root':str(root),'status':'installed','sha256':hashlib.sha256(new.encode()).hexdigest()})
assert any(r['root']=='/opt/constellation/research-publication/source'for r in results)
boto3.client('s3').put_object(Bucket='data-collection-059416028963-us-east-1-an',Key='research-data/constellation-backfill/repairs/2026-11-18-afternoon/publication-deployment-result.json',Body=json.dumps(results).encode(),ServerSideEncryption='AES256');print(json.dumps(results))
'''.replace('CHANGES',repr(changes))
(p/'install_publication_scan.py').write_text(script)
enc=base64.b64encode(script.encode()).decode();command="AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_DEFAULT_REGION=us-east-1 /opt/constellation/legacy-venv/bin/python -c \"import base64;exec(base64.b64decode('"+enc+"'))\""
(p/'publication-command.txt').write_text(command)
print('Staged command and AST equivalence verified')
