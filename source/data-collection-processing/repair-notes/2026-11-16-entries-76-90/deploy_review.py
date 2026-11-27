import json,hashlib
from pathlib import Path
from ops import remote,T3,M7,session,B,BASE,P
from metadata_engine.source_policies import build
updates=json.loads((P/'public-source-updates.json').read_text());nhs=json.loads((P/'nhsbsa-source.json').read_text());policies={k:v for k,v in build(Path.cwd()).items()if k in {*updates,'arxiv','england_nhsbsa_prescribing_data'}};(P/'policies.json').write_text(json.dumps(policies,indent=2)+'\n')
files={}
for name in ['public_source_scope.py','public_source_capture.py','open_medic_download.py','nhsbsa_capture.py','additional_source_apis.py','additional_source_plan.py','metadata_engine/raw_catalog_review.py','metadata_engine/public_documents.py','metadata_engine/nhsbsa.py','metadata_engine/evidence.py','metadata_engine/labelling.py','metadata_engine/source_policies.py','metadata_engine/controller.py','metadata_engine/streaming.py']:
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key='research-data/constellation-backfill/deployments/entries-76-90-20261116/'+sha+'/'+name;session.client('s3').put_object(Bucket=B,Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
session.client('s3').put_object(Bucket=B,Key=BASE+'policies.json',Body=(P/'policies.json').read_bytes(),ServerSideEncryption='AES256')
common=r'''import os,json,hashlib,boto3,shutil
from pathlib import Path
files=__FILES__;updates=__UPDATES__;nhs=__NHS__;policies=__POLICIES__;s=boto3.client('s3',region_name='us-east-1');bucket=__BUCKET__;base=__BASE__
def install(root,metadata=True):
 for name,ref in files.items():
  if not metadata and name.startswith('metadata_engine/'):continue
  raw=s.get_object(Bucket=bucket,Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];compile(raw,name,'exec');p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
  backup=Path('/opt/constellation/tmp/entries-76-90-backup')/root.name/name if str(root).startswith('/opt')else root/'repair-notes/2026-11-16-entries-76-90/deployed-file-backups'/name
  if p.exists()and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(p.read_bytes())
  tmp=p.with_suffix('.review.tmp');tmp.write_bytes(raw);os.chown(tmp,1000,1000);os.chmod(tmp,0o644);tmp.replace(p)
def merge(root):
 p=root/'config/constellation-public-sources.json'
 if p.exists():
  cfg=json.loads(p.read_text());seen=set()
  for i,row in enumerate(cfg['sources']):
   key=row['source']
   if key in updates:cfg['sources'][i]={**row,**updates[key]};seen.add(key)
  cfg['sources'] +=[v for k,v in updates.items()if k not in seen]
  tmp=p.with_suffix('.review.tmp');tmp.write_text(json.dumps(cfg,indent=2)+'\n');os.chown(tmp,1000,1000);tmp.replace(p)
 for name in ['specialist-inputs.json','constellation-specialist-historical.json']:
  p=root/'config'/name
  if not p.exists():continue
  cfg=json.loads(p.read_text());cfg['sources']=[r for r in cfg['sources']if r['source']!=nhs['source']]+[nhs];tmp=p.with_suffix('.review.tmp');tmp.write_text(json.dumps(cfg,indent=2)+'\n');os.chown(tmp,1000,1000);tmp.replace(p)
 p=root/'config/metadata-engine.json'
 if p.exists():
  cfg=json.loads(p.read_text())
  for key,policy in policies.items():cfg['contracts'][key]=policy;cfg.setdefault('verified_source_failure_handling',{})[key]='queue_by_source_date'
  cfg['build_sha256']=hashlib.sha256(b''.join(p.read_bytes()for p in sorted((root/'metadata_engine').glob('*.py')))).hexdigest();tmp=p.with_suffix('.review.tmp');tmp.write_text(json.dumps(cfg,indent=2)+'\n');os.chown(tmp,1000,1000);tmp.replace(p)
def routes(p):
 cfg=json.loads(p.read_text());added=[]
 for source,kind in [('ucdp_organized_violence','public'),('england_nhsbsa_prescribing_data','specialist')]:
  unit='constellation-'+kind+'-'+source+'.service'
  if any(r['unit']==unit for r in cfg['routes']):continue
  argv=(['public_source_capture.py','--source',source,'--mode','historical','--limit','2']if kind=='public'else['specialist_inputs.py','--mode','historical','--source',source,'--max-jobs','1','--pages','2','--publish','0'])
  row={'unit':unit,'route_kind':'independent_public_historical'if kind=='public'else'independent_specialist_historical','argv':argv,'start_target':'2016-01-01','end_exclusive':'2026-11-16','cadence_seconds':300,'timeout_seconds':900,'execution_enabled':True,'remaining_requirements':[],'validation_basis':'Native official public originals; bounded pages and retained checkpoints; no full-history inference','catalog_entry':78 if kind=='public'else 80,'activation_staged':False}
  if kind=='specialist':row['specialist_source']=source
  cfg['routes'].append(row);added.append(row)
 tmp=p.with_suffix('.review.tmp');tmp.write_text(json.dumps(cfg,indent=2)+'\n');os.chown(tmp,1000,1000);tmp.replace(p);return added
'''.replace('__FILES__',repr(files)).replace('__UPDATES__',repr(updates)).replace('__NHS__',repr(nhs)).replace('__POLICIES__',repr(policies)).replace('__BUCKET__',repr(B)).replace('__BASE__',repr(BASE))
code=common+r'''roots=[Path('/opt/constellation/metadata-engine-runtime'),Path('/opt/constellation/auxiliary-publication/source')]
for root in roots:install(root);merge(root)
merge(Path('/opt/constellation/source'));install(Path('/opt/constellation/source'),False)
basepath=Path('/opt/constellation');added=routes(basepath/'config/constellation-legacy-routes.json')
for source in updates:
 root=basepath/'legacy'/('constellation-public-'+source+'.service')
 if root.exists():install(root,False);merge(root)
for row in added:
 root=basepath/'legacy'/row['unit'];shutil.copytree(roots[1],root,dirs_exist_ok=True,ignore_dangling_symlinks=True,ignore=shutil.ignore_patterns('__pycache__','reports','collection-output','*.lock','.venv','*.log'))
 for p in root.rglob('*.py'):p.write_text(p.read_text().replace('/home/ec2-user/data-collection-processing',str(root)))
 (root/'.venv').unlink(missing_ok=True);(root/'.venv').symlink_to(basepath/'legacy-venv',target_is_directory=True);ram=Path('/dev/shm/constellation-legacy')/row['unit'];(ram/'locks').mkdir(parents=True,exist_ok=True)
 for name in ['reports','mlperf-evidence-cache','ted-package-cache','collection-output']:
  target=ram/'work'/name;target.mkdir(parents=True,exist_ok=True);link=root/name
  if not link.exists():link.symlink_to(target,target_is_directory=True)
 p=root/'config/constellation-specialist-historical.json';cfg=json.loads(p.read_text());cfg['backfill_end_exclusive']='2026-11-16';p.write_text(json.dumps(cfg,indent=2)+'\n')
 for folder in [root,ram]:
  for p in [folder,*folder.rglob('*')]:
   if p.exists():os.chown(p,1000,1000)
print(json.dumps({'host':'m7','files':files,'new_routes':added}))
'''
r=remote(M7,code);(P/'deployment-m7.json').write_text(r['out']);print('m7 source validators, capture fixes and two bounded historical workspaces installed.',flush=True)
code=common+r'''root=Path.cwd();install(root);merge(root);added=routes(root/'config/constellation-legacy-routes.json')
from metadata_engine.runtime_db import Database
from metadata_engine.controller import register_contract
db=Database(json.load(open('config/metadata-engine.json')))
for policy in policies.values():register_contract(db,policy)
print(json.dumps({'host':'t3','registered_contracts':list(policies),'new_routes':added}))
'''
r=remote(T3,code);(P/'deployment-t3.json').write_text(r['out']);print(r['out'])
