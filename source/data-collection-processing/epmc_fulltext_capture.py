"""Bounded Europe PMC discovery and full-text workers with independent outcomes."""
import argparse,fcntl,json,signal,time
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
from collection_storage import StorageSettings,write_json,now
from research_contract import ROOT,load_json,digest
from specialist_inputs import collect,discover_children
from specialist_plan import jobs
VERSION='epmc-fulltext-jats-context-v1'
BASE='constellation-backfill/epmc-fulltext/'
QUEUE=BASE+'discovered-jobs/'
PUBLICATION='constellation-backfill/specialist-publication-queue/epmc-fulltext/'

@contextmanager
def deadline(seconds):
 def expired(*_):raise TimeoutError('epmc_per_scope_deadline')
 previous=signal.signal(signal.SIGALRM,expired);signal.alarm(seconds)
 try:yield
 finally:signal.alarm(0);signal.signal(signal.SIGALRM,previous)

def listed(store,settings,prefix,after='',limit=50):
 base=settings.s3_prefix.rstrip('/')+'/'
 args={'Bucket':settings.s3_bucket,'Prefix':base+prefix,'MaxKeys':limit}
 if after:args['StartAfter']=base+after
 result=store.client.list_objects_v2(**args)
 return [o['Key'][len(base):]for o in result.get('Contents',[])],result.get('IsTruncated',False)

def report(store,stage,entry):
 entry={**entry,'at':now(),'stage':stage};write_json(store,BASE+'receipts/'+datetime.now(timezone.utc).date().isoformat()+'/'+digest(entry)+'.json',entry);print(json.dumps(entry),flush=True);return entry

def save_state(store,key,value):
 old=store.get(key);return write_json(store,key,value,old.token if old else None)

def load_state(store,key):
 old=store.get(key);return json.loads(old.body)if old else{}

def queue_window(store,job,result):
 if result.get('status')!='complete':return
 manifest=json.loads(store.get(result['manifest']).body)
 if manifest['status']!='complete' or not manifest['exhausted']:raise ValueError('epmc_uncommitted_window')
 identity=digest({'job':job,'manifest':result['manifest']});key=PUBLICATION+identity+'.json'
 if store.get(key)is None:write_json(store,key,{'window_id':identity,'manifests':[result['manifest']],'queued_at':now()})
 result.update(records=manifest['record_count'],window_id=identity)

def discover(store,settings,universe,taxonomy):
 import os
 os.environ['CONSTELLATION_SPECIALIST_DISCOVERY_PREFIX']=QUEUE
 state_key=BASE+'discovery-state.json';state=load_state(store,state_key);day=datetime.now(timezone.utc).date();plan=load_json(ROOT/'config/specialist-inputs.json');plan['sources']=[s for s in plan['sources']if s['source']=='europe_pmc']
 for job in jobs(plan,universe,'daily',day):
  identity=digest(job)
  if state.get('parents',{}).get(identity,{}).get('status')=='complete':continue
  try:
   with deadline(45):result=collect(job,store,settings,universe,taxonomy,2)
   if result.get('manifest'):
    discover_children(store,result['manifest'],job)
    queue_window(store,job,result)
  except Exception as error:result={'status':'failed','reason':type(error).__name__+': '+str(error)[:200]}
  entry=report(store,'parent_discovery',{'job':job,**result});state.setdefault('parents',{})[identity]=entry
  state['parents']={k:v for k,v in state['parents'].items() if v['job']['start']>=(day.replace(day=1)).isoformat() or v['status']!='complete'}
  save_state(store,state_key,state)
 # Index old shared queues incrementally; never repeatedly download the entire queue.
 for prefix in ('operations/specialists/discovered-jobs/','constellation-backfill/specialist-discovered-jobs/'):
  cursor=state.get(prefix,'');keys,more=listed(store,settings,prefix,cursor)
  for key in keys:
   try:
    job=json.loads(store.get(key).body)
    if job.get('source')=='europe_pmc_fulltext' and job.get('adapter')=='epmc_fulltext':
     target=QUEUE+digest({'source':'europe_pmc_fulltext','identity':job['parameters']['pmcid']})+'.json'
     if store.get(target)is None:write_json(store,target,job)
   except Exception as error:report(store,'legacy_discovery_index',{'key':key,'status':'failed','reason':type(error).__name__+': '+str(error)[:160]})
   state[prefix]=key;save_state(store,state_key,state)
  if not more:state[prefix]='';save_state(store,state_key,state)
  report(store,'legacy_discovery_index',{'prefix':prefix,'scanned':len(keys),'more':more,'status':'complete'})

def capture(store,settings,universe,taxonomy):
 key=BASE+'capture-state.json';state=load_state(store,key);keys,more=listed(store,settings,QUEUE,state.get('cursor',''));attempts=0;started=time.monotonic()
 for jobkey in keys:
  job=json.loads(store.get(jobkey).body);identity=digest(job);result_key=BASE+'outcomes/'+identity+'.json';prior=load_state(store,result_key)
  if (prior.get('status')!='complete' or prior.get('capture_version')!=VERSION) and (prior.get('status')=='complete' or prior.get('retry_after',0)<=time.time()):
   # Save a cooldown before external access so a killed request cannot monopolize retries.
   save_state(store,result_key,{'status':'in_progress','retry_after':time.time()+21600,'job':job})
   try:
    with deadline(75):result=collect(job,store,settings,universe,taxonomy,1)
    queue_window(store,job,result)
   except Exception as error:result={'status':'failed','reason':type(error).__name__+': '+str(error)[:200]}
   entry=report(store,'article_capture',{'job':job,**result,'capture_version':VERSION,'retry_after':time.time()+21600});save_state(store,result_key,entry);attempts+=1
  state['cursor']=jobkey;save_state(store,key,state)
  if attempts>=4 or time.monotonic()-started>180:break
 else:
  if not more:state['cursor']='';save_state(store,key,state)
 report(store,'capture_summary',{'attempted':attempts,'cursor':state.get('cursor'),'status':'complete'})

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['discover','capture'],required=True);args=parser.parse_args()
 with open('/opt/constellation/tmp/epmc-fulltext-'+args.mode+'.lock','a')as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();universe=load_json(ROOT/'config/drugsfda-inventory-universe.json');taxonomy=load_json(ROOT/'config/sectors.v1.json')
  (discover if args.mode=='discover'else capture)(store,settings,universe,taxonomy)
if __name__=='__main__':main()
