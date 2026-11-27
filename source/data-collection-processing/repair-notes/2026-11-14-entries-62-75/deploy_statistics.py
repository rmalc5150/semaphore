import json,hashlib
from pathlib import Path
from ops import remote,T3,M7,session,B,BASE,P
from metadata_engine.source_policies import build
sources=json.loads((P/'statistics-sources.json').read_text());policies={k:v for k,v in build(Path.cwd()).items()if k in {s['source']for s in sources}}
(P/'statistics-policies.json').write_text(json.dumps(policies,indent=2)+'\n')
files={}
for name in ['public_statistics_apis.py','additional_source_apis.py','additional_source_plan.py','metadata_engine/public_statistics.py','metadata_engine/evidence.py','metadata_engine/labelling.py','metadata_engine/source_policies.py','metadata_engine/controller.py','reviewed_metadata_publication.py']:
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key='research-data/constellation-backfill/deployments/entries-62-75-20261114/'+sha+'/'+name
 session.client('s3').put_object(Bucket=B,Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
common='''import json,boto3,hashlib,os,shutil,subprocess
from pathlib import Path
sources=SOURCES;policies=POLICIES;files=FILES;s=boto3.client('s3',region_name='us-east-1')
def install(root,names):
 for name in names:
  ref=files[name];raw=s.get_object(Bucket=BUCKET,Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];compile(raw,name,'exec')
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.6275.tmp');tmp.write_bytes(raw);os.chown(tmp,1000,1000);os.chmod(tmp,0o644);tmp.replace(p)
def merge_plans(root):
 for name in ['specialist-inputs.json','constellation-specialist-historical.json']:
  p=root/'config'/name
  if not p.exists():continue
  cfg=json.loads(p.read_text());seen={s['source']for s in sources};cfg['sources']=[r for r in cfg['sources']if r['source']not in seen]+sources
  tmp=p.with_suffix('.6275.tmp');tmp.write_text(json.dumps(cfg,indent=2)+'\\n');os.chown(tmp,1000,1000);tmp.replace(p)
def merge_policies(root):
 p=root/'config/metadata-engine.json';cfg=json.loads(p.read_text())
 for source,policy in policies.items():cfg['contracts'][source]=policy;cfg.setdefault('verified_source_failure_handling',{})[source]='queue_by_source_date'
 cfg['build_sha256']=hashlib.sha256(b''.join(x.read_bytes()for x in sorted((root/'metadata_engine').glob('*.py')))).hexdigest();tmp=p.with_suffix('.6275.tmp');tmp.write_text(json.dumps(cfg,indent=2)+'\\n');os.chown(tmp,1000,1000);tmp.replace(p)
def merge_routes(p):
 cfg=json.loads(p.read_text());added=[]
 for source in sources:
  unit='constellation-specialist-'+source['source']+'.service'
  if any(r['unit']==unit for r in cfg['routes']):continue
  row={'unit':unit,'route_kind':'independent_specialist_historical','specialist_source':source['source'],'argv':['specialist_inputs.py','--mode','historical','--lane','default','--source',source['source'],'--max-jobs','1','--pages','2','--publish','0'],'start_target':'2016-01-01','end_exclusive':'2026-11-14','cadence_seconds':300,'timeout_seconds':900,'execution_enabled':True,'remaining_requirements':[],'validation_basis':source['coverage_note'],'catalog_entry':int(source['source_id'][1:]),'activation_staged':False};cfg['routes'].append(row);added.append(row)
 tmp=p.with_suffix('.6275.tmp');tmp.write_text(json.dumps(cfg,indent=2)+'\\n');os.chown(tmp,1000,1000);tmp.replace(p);return added
'''.replace('SOURCES',repr(sources)).replace('POLICIES',repr(policies)).replace('FILES',repr(files)).replace('BUCKET',repr(B))
# m7 code and isolated workspaces first; controller dispatchers are installed after capture verification.
code=common+'''roots=[Path('/opt/constellation/metadata-engine-runtime'),Path('/opt/constellation/auxiliary-publication/source')]
for root in roots:install(root,files);merge_plans(root);merge_policies(root)
base=Path('/opt/constellation');merge_routes(base/'config/constellation-legacy-routes.json')
for source in sources:
 unit='constellation-specialist-'+source['source']+'.service';root=base/'legacy'/unit
 if not (root/'.statistics-ready').exists():
  shutil.copytree(roots[1],root,dirs_exist_ok=True,ignore_dangling_symlinks=True,ignore=shutil.ignore_patterns('__pycache__','reports','collection-output','*.lock','.venv','*.log'))
  for p in root.rglob('*.py'):
   p.write_text(p.read_text().replace('/home/ec2-user/data-collection-processing',str(root)))
  (root/'.venv').unlink(missing_ok=True)
  (root/'.venv').symlink_to(base/'legacy-venv',target_is_directory=True)
  ram=Path('/dev/shm/constellation-legacy')/unit
  for name in ('reports','mlperf-evidence-cache','ted-package-cache','collection-output'):
   target=ram/'work'/name;target.mkdir(parents=True,exist_ok=True);link=root/name
   if not link.exists():link.symlink_to(target,target_is_directory=True)
  (ram/'locks').mkdir(parents=True,exist_ok=True)
  for folder in [root,ram]:
   for p in [folder,*folder.rglob('*')]:
    if p.exists():os.chown(p,1000,1000)
 install(root,files);merge_plans(root);(root/'.statistics-ready').touch()
print(json.dumps({'installed_sources':[s['source']for s in sources],'files':files}))
'''
r=remote(M7,code);(P/'statistics-deployment-m7.json').write_text(r['out']);print('m7 runtime and workspaces installed',flush=True)
code=common+'''root=Path.cwd();install(root,files);merge_plans(root);merge_policies(root);merge_routes(root/'config/constellation-legacy-routes.json')
from metadata_engine.runtime_db import Database
from metadata_engine.controller import register_contract
db=Database(json.loads((root/'config/metadata-engine.json').read_text()))
for policy in policies.values():register_contract(db,policy)
print(json.dumps({'registered':list(policies),'dispatchers':'pending native capture verification'}))
'''
r=remote(T3,code);(P/'statistics-deployment-t3.json').write_text(r['out']);print(r['out'])
