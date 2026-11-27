"""Independent bounded grants/procurement capture; failures remain scoped to their source/window."""
import argparse,fcntl,json,time
from pathlib import Path
from datetime import datetime,timezone,date,timedelta
from research_contract import ROOT,load_json,digest
from collection_storage import StorageSettings,write_json,now
from specialist_inputs import collect
from specialist_plan import jobs
from cms_coverage_capture import deadline,queue_metadata
SOURCES=('nih_reporter','usa_spending','ted_notices','uspto_assignment_histories','nist_robotics_methods')
BASE='constellation-backfill/grants-review/'
QUEUE='constellation-backfill/specialist-publication-queue/grants-review/'

def completed_summary(planned, state):
 if not planned:return None
 results=[]
 for job in planned:
  prior=state.get('windows',{}).get(digest(job),{})
  if (prior.get('job')!=job or prior.get('status')!='complete'
      or not str(prior.get('manifest','')).startswith('manifests/collection_runs/')):
   return None
  results.append({'status':'complete','manifest':prior['manifest']})
 return {'status':'complete','reviewed_scope_only':True,'completed_scopes':len(results),'results':results}

def save(store,key,value):
 old=store.get(key);write_json(store,key,value,old.token if old else None)

def plan_jobs(plan,universe,day,probe=False,mode='daily'):
 # Probe the same configured daily scopes; partial pages remain resumable.
 result=list(jobs(plan,universe,mode,day))
 nist=next((j for j in result if j['source']=='nist_robotics_methods'),None)
 if nist:
  from copy import deepcopy
  methods=[]
  for url in ('https://www.nist.gov/system/files/documents/2020/11/04/NIST_Grasp_Performance_Study.pdf','https://www.nist.gov/el/intelligent-systems-division-73500/robotic-grasping-and-manipulation-assembly/grasping'):
   job=deepcopy(nist);job['parameters']['url']=url;job['coverage_note']='Current retrieval of original NIST robotics method/report; original publication date does not establish a historical retrieval vintage.';methods.append(job)
  result=methods+result
 return result

def _capture_one(store,settings,universe,taxonomy,job,pages=2):
 try:
  with deadline(100):result=collect(job,store,settings,universe,taxonomy,pages)
  if result.get('manifest')and result.get('status')in ('partial','complete'):
   m=json.loads(store.get(result['manifest']).body);queue_metadata(store,m)
   if result['status']=='complete':
    if m['status']!='complete'or not m['exhausted']:raise ValueError('grants_uncommitted_window')
    identity=digest({'job':job,'manifest':result['manifest']});key=QUEUE+identity+'.json'
    if store.get(key)is None:write_json(store,key,{'window_id':identity,'manifests':[result['manifest']],'queued_at':now()})
    result.update(records=m['record_count'],window_id=identity)
 except Exception as error:result={'status':'partial' if type(error).__name__=='Conflict' else 'failed','reason':type(error).__name__+': '+str(error)[:250]}
 entry={'job':job,**result,'at':now(),'retry_after':time.time()+(21600 if result.get('status')=='failed'else 90)}
 write_json(store,BASE+'receipts/'+digest(entry)+'.json',entry);print(json.dumps(entry),flush=True);return entry

def capture_one(store,settings,universe,taxonomy,job,pages=2):
 directory=Path('/opt/constellation/tmp') if Path('/opt/constellation/tmp').exists() else ROOT/'state'
 directory.mkdir(parents=True,exist_ok=True)
 with (directory/('grants-scope-'+digest(job)+'.lock')).open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:
   entry={'job':job,'status':'deferred','reason':'same_scope_active','retry_after':time.time()+90,'at':now()};print(json.dumps(entry),flush=True);return entry
  return _capture_one(store,settings,universe,taxonomy,job,pages)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--sources',nargs='+',choices=SOURCES,required=True);parser.add_argument('--probe',action='store_true');parser.add_argument('--mode',choices=['daily','historical'],default='daily');parser.add_argument('--universe',default='config/company-universe.v0.3.json');args=parser.parse_args();identity=args.mode+'-'+digest(sorted(args.sources))[:12];directory=Path('/opt/constellation/tmp')if Path('/opt/constellation/tmp').exists()else ROOT/'state/grants-review';directory.mkdir(parents=True,exist_ok=True)
 with (directory/('grants-review-'+identity+'.lock')).open('a')as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();universe=load_json(ROOT/args.universe);taxonomy=load_json(ROOT/'config/sectors.v1.json');plan=load_json(ROOT/'config/specialist-inputs.json');plan['sources']=[s for s in plan['sources']if s['source']in args.sources];day=datetime.now(timezone.utc).date();planned=plan_jobs(plan,universe,day,args.probe,args.mode)
  if args.probe:
   for source in args.sources:
    selected=next((j for j in planned if j['source']==source),None)
    if selected:capture_one(store,settings,universe,taxonomy,selected,1)
   return
  key=BASE+'state-'+identity+'.json';old=store.get(key);state=json.loads(old.body)if old else{};cursor=state.get('source_cursor',0);attempted=0
  for i in range(len(args.sources)):
   source=args.sources[(cursor+i)%len(args.sources)]
   for job in [j for j in planned if j['source']==source]:
    prior=state.get('windows',{}).get(digest(job),{})
    if prior.get('status')=='complete'or prior.get('retry_after',0)>time.time():continue
    result=capture_one(store,settings,universe,taxonomy,job);state.setdefault('windows',{})[digest(job)]=result;state['source_cursor']=(cursor+i+1)%len(args.sources);save(store,key,state);attempted+=1;break
   if attempted>=2:break
  if attempted==0:
   summary=completed_summary(planned,state)
   if summary:print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
