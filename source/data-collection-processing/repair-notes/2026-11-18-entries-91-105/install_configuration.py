from ops import *
import hashlib
raw=session.client('s3').get_object(Bucket=B,Key=BASE+'capture-proof.json')['Body'].read();proof=json.loads(raw);(P/'capture-proof.json').write_bytes(raw)
eligible={k for k,v in proof['public'].items()if v['status']=='verified'}
eligible|={k for k,modes in proof['native'].items()if set(modes)=={'daily','historical'}and all(m['status']=='verified'for m in modes.values())}
updates={k:v for k,v in json.loads((P/'public-source-updates.json').read_text()).items()if k in eligible or k=='cninfo_mainland_china_company_disclosures'and k in eligible};native={k:v for k,v in json.loads((P/'native-source-updates.json').read_text()).items()if k in eligible};policies={k:v for k,v in json.loads((P/'policies.json').read_text()).items()if k in eligible};daily=[{**r,'execution_enabled':True,'activation_staged':False,'remaining_requirements':[]}for r in json.loads((P/'worker-daily-route-additions.json').read_text())if any(k in r['unit']for k in eligible)]
fix=Path('constellation/legacy_dispatch.py').read_bytes();fixsha=hashlib.sha256(fix).hexdigest();fixkey=BASE+'deployment/legacy_dispatch-'+fixsha+'.py';session.client('s3').put_object(Bucket=B,Key=fixkey,Body=fix,ServerSideEncryption='AES256')
common=r'''import json,os,hashlib,shutil,boto3
from pathlib import Path
updates=UPDATES;native=NATIVE;policies=POLICIES;daily=DAILY;s=boto3.client('s3',region_name='us-east-1');bucket=BUCKET
backup=Path('/opt/constellation/tmp/entries-91-105-config-backups')if WORKER else Path.cwd()/'repair-notes/2026-11-18-entries-91-105/config-before'
def save(p,value):
 label=hashlib.sha256(str(p).encode()).hexdigest()[:16];old=backup/(label+'-'+p.name)
 if p.exists()and not old.exists():backup.mkdir(parents=True,exist_ok=True);old.write_bytes(p.read_bytes())
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.review.tmp');tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n');os.chown(tmp,1000,1000);tmp.replace(p)
def merge(root,workspace=False):
 p=root/'config/constellation-public-sources.json'
 if p.exists():
  cfg=json.loads(p.read_text());seen=set()
  for i,row in enumerate(cfg['sources']):
   if row['source']in updates:cfg['sources'][i]={**row,**updates[row['source']]};seen.add(row['source'])
  cfg['sources'] +=[v for k,v in updates.items()if k not in seen];save(p,cfg)
 for name in ['specialist-inputs.json','constellation-specialist-historical.json']:
  p=root/'config'/name
  if not p.exists():continue
  cfg=json.loads(p.read_text());seen=set()
  for i,row in enumerate(cfg['sources']):
   key=row['source']
   if key in native:cfg['sources'][i]={**row,**native[key],'execution_lane':'default'if workspace or name=='constellation-specialist-historical.json'else'independent_public_daily'};seen.add(key)
  cfg['sources'] +=[{**v,'execution_lane':'default'if workspace or name=='constellation-specialist-historical.json'else'independent_public_daily'}for k,v in native.items()if k not in seen];save(p,cfg)
 p=root/'config/metadata-engine.json'
 if p.exists():
  cfg=json.loads(p.read_text())
  for k,policy in policies.items():cfg['contracts'][k]=policy;cfg.setdefault('verified_source_failure_handling',{})[k]='queue_by_source_date'
  cfg['build_sha256']=hashlib.sha256(b''.join(p.read_bytes()for p in sorted((root/'metadata_engine').glob('*.py')))).hexdigest();save(p,cfg)
def route_merge(path):
 cfg=json.loads(path.read_text());added=[]
 if 'cninfo_mainland_china_company_disclosures'in native:
  for row in cfg['routes']:
   if row['unit']=='constellation-public-cninfo_mainland_china_company_disclosures.service':row.update(execution_enabled=False,activation_staged=False,remaining_requirements=['Replaced by native CNINFO index and original-document collector'])
  unit='constellation-specialist-cninfo_mainland_china_company_disclosures.service'
  if not any(r['unit']==unit for r in cfg['routes']):
   row={'unit':unit,'route_kind':'independent_specialist_historical','specialist_source':'cninfo_mainland_china_company_disclosures','argv':['specialist_inputs.py','--mode','historical','--source','cninfo_mainland_china_company_disclosures','--max-jobs','1','--pages','4','--publish','0'],'start_target':'2016-01-01','end_exclusive':'2026-11-18','cadence_seconds':300,'timeout_seconds':900,'execution_enabled':True,'activation_staged':False,'remaining_requirements':[],'catalog_entry':92,'validation_basis':'Native announcement rows paired with matched original PDF; bounded monthly scopes, no exhaustive coverage assertion'};cfg['routes'].append(row);added.append(row)
 for row in daily:
  if not any(r['unit']==row['unit']for r in cfg['routes']):cfg['routes'].append(row);added.append(row)
 save(path,cfg);return added
fix=s.get_object(Bucket=bucket,Key=FIXKEY)['Body'].read();assert hashlib.sha256(fix).hexdigest()==FIXSHA
def install_fix(root):
 p=root/'constellation/legacy_dispatch.py';p.write_bytes(fix);os.chown(p,1000,1000)
def clone(target,template):
 if target.exists():return
 target.mkdir(parents=True)
 for source in template.glob('*.py'):
  (target/source.name).write_text(source.read_text().replace('/home/ec2-user/data-collection-processing',str(target)))
 for folder in ('config','schemas','constellation','metadata_engine'):
  src=template/folder
  if src.exists():shutil.copytree(src,target/folder,dirs_exist_ok=True,ignore_dangling_symlinks=True,ignore=shutil.ignore_patterns('__pycache__','daily-workspaces','*.lock'))
 for p in target.rglob('*.py'):
  p.write_text(p.read_text().replace('/home/ec2-user/data-collection-processing',str(target)))
def ownership(root):
 for p in [root,*root.rglob('*')]:
  if p.exists()and not p.is_symlink():os.chown(p,1000,1000)
'''.replace('UPDATES',repr(updates)).replace('NATIVE',repr(native)).replace('POLICIES',repr(policies)).replace('DAILY',repr(daily)).replace('BUCKET',repr(B)).replace('FIXKEY',repr(fixkey)).replace('FIXSHA',repr(fixsha))
worker=common.replace('WORKER','True')+r'''
base=Path('/opt/constellation');template=base/'auxiliary-publication/source';roots=[base/'metadata-engine-runtime',template,base/'source'];added=route_merge(base/'config/constellation-legacy-routes.json')
for row in added:
 root=base/'legacy'/row['unit'];clone(root,template);ram=Path('/dev/shm/constellation-legacy')/row['unit'];(ram/'locks').mkdir(parents=True,exist_ok=True)
 for name in ('reports','mlperf-evidence-cache','ted-package-cache','collection-output'):
  target=ram/'work'/name;target.mkdir(parents=True,exist_ok=True);link=root/name
  if not link.exists():link.symlink_to(target,target_is_directory=True)
 link=root/'.venv'
 if not link.exists():link.symlink_to(base/'legacy-venv',target_is_directory=True)
 ownership(root);ownership(ram)
for source in policies:
 for kind in ('public','specialist'):
  root=base/'legacy'/('constellation-'+kind+'-'+source+'.service')
  if root.exists():roots.append(root)
for row in daily:
 root=base/'legacy'/row['unit']
 if root not in roots:roots.append(root)
for root in roots:
 merge(root,'/legacy/'in str(root));install_fix(root)
 p=root/'config/constellation-legacy-routes.json'
 if p.exists():route_merge(p)
print(json.dumps({'host':'worker','sources':list(policies),'added_routes':[r['unit']for r in added],'roots':[str(r)for r in roots]}))
'''
print(remote(M7,worker)['out'])
controller=common.replace('WORKER','False')+r'''
root=Path.cwd();merge(root);install_fix(root);added=route_merge(root/'config/constellation-legacy-routes.json')
for source in native:
 target=root/'constellation/daily-workspaces'/source;clone(target,root/'constellation/daily-workspaces/south_korea_fss_opendart')
 # Refresh the actual collector dependencies; do not copy private runtime state.
 for name in ['specialist_inputs.py','additional_source_apis.py','filing_originals_capture.py','regional_source_review.py','provider_tls.py']:
  (target/name).write_bytes((root/name).read_bytes());os.chown(target/name,1000,1000)
 merge(target,True);ownership(target)
p=root/'constellation/expansion/new-adapters.json';definitions=json.loads(p.read_text())
for source,spec in native.items():
 row={'entry':92 if source.startswith('cninfo')else 98,'source':source,'adapter':'cninfo'if source.startswith('cninfo')else'dart','scope_note':spec['coverage_note'],'daily_enabled':True};definitions=[d for d in definitions if d['source']!=source]+[row]
save(p,definitions)
print(json.dumps({'host':'controller','sources':list(policies),'added_routes':[r['unit']for r in added],'daily_workspaces':list(native)}))
'''
r=remote(T3,controller);print(r['out']);(P/'configuration-installed.json').write_text(json.dumps({'sources':sorted(eligible),'controller':json.loads(r['out'])},indent=2)+'\n')
