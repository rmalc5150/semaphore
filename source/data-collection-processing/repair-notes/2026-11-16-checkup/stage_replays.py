import boto3,json
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3',region_name='us-east-1');b='data-collection-059416028963-us-east-1-an';base='research-data/constellation-backfill/repairs/2026-11-16'
s.put_object(Bucket=b,Key=base+'/jobs.json',Body=(p/'replay-jobs.json').read_bytes(),ServerSideEncryption='AES256')
script=r'''import os,sys,json,time,traceback
from pathlib import Path
from datetime import datetime,timezone,timedelta
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
import boto3
from collection_storage import StorageSettings,write_json,now,Conflict
from research_contract import load_json,digest
from specialist_inputs import collect,discover_children
settings=StorageSettings.load(root/'config/collection-storage.s3.json');store=settings.store();u=load_json(root/'config/company-universe.v0.5.json');t=load_json(root/'config/sectors.v1.json')
bucket='data-collection-059416028963-us-east-1-an';base='research-data/constellation-backfill/repairs/2026-11-16';s=boto3.client('s3');jobs=json.loads(s.get_object(Bucket=bucket,Key=base+'/jobs.json')['Body'].read());out=[]
for entry in jobs:
 job=entry['job'];identity=entry['identity'];started=now();key='constellation-backfill/specialist-schedulers/constellation-specialist-'+job['source']+'.service/historical.json'
 try:
  assert identity==digest({'job':job,'universe_hash':digest(u),'version':'specialist-inputs-1.2'}),'universe differs from original task'
  result=collect(job,store,settings,u,t,entry['pages'])
  row={**result,'job_id':identity,'job':job,'source':job['source'],'source_id':job['source_id'],'start':job['start'],'end_exclusive':job['end'],'last_attempt':now()}
  if result.get('reason')=='census_period_not_yet_published' or result['status']=='failed':row['retry_after']=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat().replace('+00:00','Z')
  saved=store.get(key);state=json.loads(saved.body);prior=state['jobs'].get(identity,{})
  if prior.get('last_attempt','')>started:raise Conflict('concurrent source attempt; scheduler update deferred')
  state['jobs'][identity]=row;state['updated_at']=now();write_json(store,key,state,saved.token)
  if result['status']=='complete':
   q='operations/specialists/publication-queue/'+identity+'.json'
   if store.get(q)is None:write_json(store,q,{'window_id':identity,'manifests':[result['manifest']],'queued_at':now()})
  row['scheduler_updated']=True
 except Exception as e:
  row={'job_id':identity,'source':job['source'],'start':job['start'],'status':'repair_failed','reason':type(e).__name__+':'+str(e)[:300]}
 out.append(row);s.put_object(Bucket=bucket,Key=base+'/steps/'+identity+'.json',Body=json.dumps(row,default=str).encode(),ServerSideEncryption='AES256');print(json.dumps(row),flush=True)
result={'at':now(),'outcomes':out};s.put_object(Bucket=bucket,Key=base+'/replay-results.json',Body=json.dumps(result).encode(),ServerSideEncryption='AES256');print(json.dumps({'finished':True,'counts':{v:sum(x['status']==v for x in out)for v in set(x['status']for x in out)}}),flush=True)
'''
s.put_object(Bucket=b,Key=base+'/replay.py',Body=script.encode(),ServerSideEncryption='AES256')
launch="""import boto3,subprocess,json
from pathlib import Path
s=boto3.client('s3');p=Path('/opt/constellation/tmp/checkup1116');p.mkdir(exist_ok=True,parents=True);f=p/'replay.py';f.write_bytes(s.get_object(Bucket='data-collection-059416028963-us-east-1-an',Key='research-data/constellation-backfill/repairs/2026-11-16/replay.py')['Body'].read())
r=subprocess.run(['systemd-run','--unit=optima-checkup-1116-replays','--property=Slice=constellation-workers.slice','--property=MemoryMax=1536M','--property=CPUQuota=50%','--property=RuntimeMaxSec=1800','--property=StandardOutput=append:'+str(p/'replay.log'),'--property=StandardError=append:'+str(p/'replay.log'),'--setenv=AWS_CONFIG_FILE=/dev/null','--setenv=AWS_SHARED_CREDENTIALS_FILE=/dev/null','--setenv=AWS_DEFAULT_REGION=us-east-1','/opt/constellation/legacy-venv/bin/python',str(f)],capture_output=True,text=True);print(r.returncode,r.stdout,r.stderr);assert r.returncode==0
"""
(p/'launch_replays.py').write_text(launch);print('staged 74 isolated replay steps')
