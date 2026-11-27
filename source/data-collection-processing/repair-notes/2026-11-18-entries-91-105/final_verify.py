from ops import *
import hashlib
files={n:hashlib.sha256(Path(n).read_bytes()).hexdigest()for n in json.loads((P/'deployment-plan.json').read_text())['files']if not n.startswith('constellation/')};files['public_source_capture.py']=hashlib.sha256(Path('public_source_capture.py').read_bytes()).hexdigest();files['regional_source_review.py']=hashlib.sha256(Path('regional_source_review.py').read_bytes()).hexdigest()
worker=r'''import json,hashlib,os,subprocess,boto3
from pathlib import Path
files=FILES;roots=[Path('/opt/constellation/metadata-engine-runtime'),Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/source')];out={'code':{},'daily_services':{},'memory':subprocess.check_output(['free','-m'],text=True)}
for root in roots:
 for name,sha in files.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,str(root/name)
 p=root/'config/metadata-engine.json'
 if not p.exists():out['code'][str(root)]={'files_checked':len(files),'metadata_config':'not used in seed root'};continue
 cfg=json.loads(p.read_text());sha=hashlib.sha256(b''.join(v.read_bytes()for v in sorted((root/'metadata_engine').glob('*.py')))).hexdigest()
 if cfg.get('build_sha256')!=sha:
  cfg['build_sha256']=sha;tmp=p.with_name(p.name+'.verified-build');tmp.write_text(json.dumps(cfg,indent=2)+'\n');os.chown(tmp,1000,1000);tmp.replace(p)
 out['code'][str(root)]={'files_checked':len(files),'metadata_build_sha256':sha}
for name in ['public-ndb-daily','public-indonesia-minerals-daily','public-cfem-daily']:
 unit='optima-m7-capture-'+name+'.service';props=dict(line.split('=',1)for line in subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','-p','Result','-p','ExecMainStatus'],text=True).splitlines());assert props['Result']=='success'and props['ExecMainStatus']=='0',props;out['daily_services'][unit]=props
listing=subprocess.check_output(['systemctl','list-units','--state=active','--plain','--no-legend','constellation-backfill@*.service','constellation-legacy-worker@*.service','constellation-public-worker@*.service'],text=True);out['active_historical_workers']=[l.split()[0]for l in listing.splitlines()if l.strip()];assert len(out['active_historical_workers'])==15
out['batch_paused']=Path('/opt/constellation/batch-paused').exists();assert not out['batch_paused']
s=boto3.client('s3',region_name='us-east-1');s.put_object(Bucket=BUCKET,Key=BASE+'worker-verified.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print(json.dumps({'code_roots':list(out['code']),'active_historical_workers':len(out['active_historical_workers']),'daily_services_successful':len(out['daily_services']),'batch_paused':out['batch_paused']}))
'''.replace('FILES',repr(files)).replace('BUCKET',repr(B)).replace('BASE',repr(BASE))
print(remote(M7,worker)['out'])
controller=r'''import json,boto3,subprocess
from pathlib import Path
from constellation.control import Control
from metadata_engine.runtime_db import Database
from public_source_capture import read_json,PREFIX
from source_pauses import is_paused
sources=SOURCES;c=Control();cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);public={r['source']:r for r in json.load(open('config/constellation-public-sources.json'))['sources']};out={'sources':{},'daily':{},'historical':[],'historical_raw':{},'timers':{},'paused_sources':json.load(open('config/source-pauses.json'))['sources']};activation=json.loads(c.s3.get_object(Bucket=BUCKET,Key=BASE+'activation.json')['Body'].read())
for source in sources:
 entry={}
 with db.tx()as q:
  q.execute('SET SESSION max_execution_time=3000');q.execute('SELECT state,contract_version,consecutive_raw_failures,last_reason FROM engine_sources WHERE source_key=%s',(source,));entry['control']=q.fetchone();q.execute('SELECT state,count(*) jobs FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s GROUP BY state',(source,));entry['counts']=q.fetchall()
 if 'kosis'not in source:assert entry['control']['state']=='enabled'and entry['control']['contract_version']=='2.0.3',source
 out['sources'][source]=entry
 if source in public and public[source].get('enabled',True):
  spec=public[source];key=PREFIX+'/states/daily/'+source+'/'+spec['raw_content_revision']+'.json';v,_=read_json(c.s3,key);out['daily'][source]={'captured_urls':len(v['done']),'failed_urls':len(v['failures']),'remaining_urls':len(v['frontier'])}if v else{'missing_state':True}
 elif source in ('cninfo_mainland_china_company_disclosures','south_korea_fss_opendart'):
  key='research-data/constellation-backfill/daily-api-schedulers/'+source+'/daily.json';v,_=read_json(c.s3,key);assert v and v.get('jobs'),source
  from collections import Counter
  recent=sorted(v['jobs'].values(),key=lambda r:r.get('last_attempt',''),reverse=True)
  out['daily'][source]={'job_states':dict(Counter(r.get('status')for r in recent)),'latest_status':recent[0]['status'],'last_attempt':recent[0].get('last_attempt')};assert recent[0]['status']in ('partial','complete'),source
for source,spec in public.items():
 if source not in sources or not spec.get('enabled',True):continue
 key=PREFIX+'/states/historical/'+source+'/'+spec['raw_content_revision']+'.json';v,_=read_json(c.s3,key)
 assert v and v['done']and not v['failures'],(source,v.get('failures')if v else'missing historical state')
 out['historical_raw'][source]={'captured_urls':len(v['done']),'remaining_urls':len(v['frontier']),'failed_urls':len(v['failures'])}
for job in activation['historical_lanes']:
 r=c.get('job#'+job['job_id']);result=json.loads(r['result_json']or'{}');out['historical'].append({'unit':job['unit'],'job_id':job['job_id'],'status':r['status'],'checkpoint_verified':result.get('checkpoint_verified'),'report_uri':result.get('report_uri')})
 if 'opendart'not in job['unit']:assert r['status']=='succeeded'and result.get('checkpoint_verified'),job['unit']
for unit in ['constellation-public-daily.timer','constellation-public-api-daily.timer','constellation-historical-dispatch.timer','optima-m7-shared-autostop.timer','optima-public-ndb-daily.timer','optima-public-indonesia-minerals-daily.timer','optima-public-cfem-daily.timer']:
 props=dict(l.split('=',1)for l in subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','-p','NextElapseUSecRealtime'],text=True).splitlines());out['timers'][unit]=props;assert props['ActiveState']=='active',unit
for source,data in out['daily'].items():
 if 'failed_urls'in data:assert data['failed_urls']==0,(source,data)
assert is_paused('reddit')and is_paused('github_sdk')and not next(r for r in public.values()if r['source']=='nice_technology_appraisals')['enabled']
out['historical_allowed']=c.allowed();out['daily_allowed']=c.daily_allowed();out['policy']=json.load(open('config/m7-batch-policy.json'));out['batch_state']={k:json.load(open('constellation/autostop/m7-batch.json')).get(k)for k in ('phase','started_at','wake_reason')}
c.s3.put_object(Bucket=BUCKET,Key=BASE+'controller-verified.json',Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256');print(json.dumps({'source_count':len(out['sources']),'daily_checkpoints':len(out['daily']),'historical_verified':sum(r['checkpoint_verified']is True for r in out['historical']),'historical_running':[r['unit']for r in out['historical']if r['status']=='running'],'active_timers':len(out['timers']),'deliberate_pauses_preserved':True}))
'''.replace('SOURCES',repr(SOURCES)).replace('BUCKET',repr(B)).replace('BASE',repr(BASE))
print(remote(T3,controller)['out'])
for name in ['worker-verified.json','controller-verified.json','activation-status.json','nhsa-daily-recovery.json','withdrawal-verified.json']:(P/name).write_bytes(session.client('s3').get_object(Bucket=B,Key=BASE+name)['Body'].read())
