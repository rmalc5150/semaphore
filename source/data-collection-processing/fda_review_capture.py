"""Independent bounded FDA capture; failures remain scoped to their source/window."""
import argparse,fcntl,json,time
from pathlib import Path
from datetime import datetime,timezone,date,timedelta
from research_contract import ROOT,load_json,digest
from collection_storage import StorageSettings,write_json,now
from specialist_inputs import collect
from specialist_plan import jobs
from cms_coverage_capture import deadline,queue_metadata
SOURCES=('fda_dd_compliance_actions','fda_dd_import_refusals','fda_dd_inspections_citations','fda_ires_recalls','fda_product_codes')
BASE='constellation-backfill/fda-review/'
QUEUE='constellation-backfill/specialist-publication-queue/fda-review/'
PROBE_DATES={'fda_dd_compliance_actions':'2026-07-27','fda_dd_import_refusals':'2026-07-02','fda_dd_inspections_citations':'2026-09-16','fda_ires_recalls':'2026-10-28'}

def save(store,key,value):
 old=store.get(key);write_json(store,key,value,old.token if old else None)

def plan_jobs(plan,universe,day,probe=False):
 if not probe:
  return list(jobs(plan,universe,'daily',day))
 result=[]
 for source in plan['sources']:
  start=PROBE_DATES.get(source['source'],day.isoformat());end=(date.fromisoformat(start)+timedelta(days=1)).isoformat();p={'url':source['api']}
  if source['source']!='fda_product_codes':p.update(start=start,end=end)
  if source.get('date_field'):p['date_field']=source['date_field']
  result.append({'source':source['source'],'source_id':source['source_id'],'adapter':source['adapter'],'mode':'historical'if source['source']!='fda_product_codes'else'daily','start':start,'end':end,'parameters':p,'coverage_note':source['coverage_note']+' One-date verification window only.'})
 return result

def capture_one(store,settings,universe,taxonomy,job,pages=2):
 try:
  with deadline(100):result=collect(job,store,settings,universe,taxonomy,pages)
  if result.get('manifest')and result.get('status')in ('partial','complete'):
   m=json.loads(store.get(result['manifest']).body);queue_metadata(store,m)
   if result['status']=='complete':
    if m['status']!='complete'or not m['exhausted']:raise ValueError('fda_uncommitted_window')
    identity=digest({'job':job,'manifest':result['manifest']});key=QUEUE+identity+'.json'
    if store.get(key)is None:write_json(store,key,{'window_id':identity,'manifests':[result['manifest']],'queued_at':now()})
    result.update(records=m['record_count'],window_id=identity)
 except Exception as error:result={'status':'failed','reason':type(error).__name__+': '+str(error)[:250]}
 entry={'job':job,**result,'at':now(),'retry_after':time.time()+(21600 if result.get('status')=='failed'else 90)}
 write_json(store,BASE+'receipts/'+digest(entry)+'.json',entry);print(json.dumps(entry),flush=True);return entry

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--sources',nargs='+',choices=SOURCES,required=True);parser.add_argument('--probe',action='store_true');parser.add_argument('--universe',default='config/drugsfda-inventory-universe.json');args=parser.parse_args();identity=digest(sorted(args.sources))[:12]+('-probe'if args.probe else'');directory=Path('/opt/constellation/tmp')if Path('/opt/constellation/tmp').exists()else ROOT/'state/fda-review';directory.mkdir(parents=True,exist_ok=True)
 with (directory/('fda-review-'+identity+'.lock')).open('a')as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();universe=load_json(ROOT/args.universe);taxonomy=load_json(ROOT/'config/sectors.v1.json');plan=load_json(ROOT/'config/specialist-inputs.json');plan['sources']=[s for s in plan['sources']if s['source']in args.sources];day=datetime.now(timezone.utc).date();planned=plan_jobs(plan,universe,day,args.probe)
  if args.probe:
   for job in planned:capture_one(store,settings,universe,taxonomy,job,6)
   return
  key=BASE+'state-'+identity+'.json';old=store.get(key);state=json.loads(old.body)if old else{};cursor=state.get('source_cursor',0);attempted=0
  for i in range(len(args.sources)):
   source=args.sources[(cursor+i)%len(args.sources)]
   for job in [j for j in planned if j['source']==source]:
    prior=state.get('windows',{}).get(digest(job),{})
    if prior.get('status')=='complete'or prior.get('retry_after',0)>time.time():continue
    result=capture_one(store,settings,universe,taxonomy,job);state.setdefault('windows',{})[digest(job)]=result;state['source_cursor']=(cursor+i+1)%len(args.sources);save(store,key,state);attempted+=1;break
   if attempted>=2:break
if __name__=='__main__':main()
