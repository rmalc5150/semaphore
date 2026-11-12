"""Bounded NMPA worker capture; original backfill seed plus S3 outcome checkpoints."""
import argparse,fcntl,hashlib,json,sqlite3,os,time,signal
from datetime import datetime,timedelta,timezone,date
from pathlib import Path
import boto3
from collection_storage import StorageSettings,write_json,now,task_spec
from research_contract import ROOT,load_json,digest
from regulatory_collection import EvidenceClient,SourceIssue
from nmpa_baseline import inventory,VERSION as INVENTORY_VERSION,COVERAGE as INVENTORY_COVERAGE
from nmpa_enrichment_worker import capture,output_rows
PREFIX='constellation-backfill/legacy-operation-receipts/nmpa-resumed'

def put_state(store,key,value):
 old=store.get(key);write_json(store,key,value,old.token if old else None)

def reserve(store,limit):
 from collection_storage import Conflict
 key=PREFIX+'/budgets/'+now()[:10]+'.json'
 for _ in range(3):
  old=store.get(key);used=json.loads(old.body)['reserved']if old else 0
  if used+4>limit:return False
  try:write_json(store,key,{'reserved':used+4,'limit':limit,'at':now()},old.token if old else None);return True
  except Conflict:continue
 return False

def seed_database(config):
 ref=config['seed'];target=Path('/opt/constellation/tmp')/('nmpa-resumed-seed-'+ref['sha256']+'.sqlite3')
 if not target.exists():
  tmp=target.with_suffix('.download');boto3.client('s3',region_name='us-east-1').download_file(ref['bucket'],ref['key'],str(tmp))
  h=hashlib.sha256()
  with tmp.open('rb')as f:
   for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
  if h.hexdigest()!=ref['sha256']:tmp.unlink();raise ValueError('nmpa_seed_checksum_mismatch')
  os.chmod(tmp,0o400);tmp.replace(target)
 return sqlite3.connect('file:'+str(target)+'?mode=ro',uri=True)

def inventory_context(store,config):
 head=json.loads(store.get(config['inventory_checkpoint']).body);task=head['task'];universe=json.loads(store.get('manifests/configurations/universe/'+task['universe_hash']+'.json').body);taxonomy=json.loads(store.get('manifests/configurations/taxonomy/'+task['taxonomy_hash']+'.json').body)
 return head,universe,taxonomy

def daily_head_key(universe,taxonomy):
 today=datetime.now(timezone.utc).date();stamp=lambda d:d.isoformat()+'T00:00:00Z'
 spec=task_spec('nmpa_trials','registry_inventory','daily',stamp(today),stamp(today+timedelta(days=1)),{'coverage':INVENTORY_COVERAGE,'listing_page_size':20,'snapshot_date':today.isoformat()},INVENTORY_VERSION,universe,taxonomy)
 return 'checkpoints/task_'+digest(spec)+'/head.json'

def cached_inventory_ids(store,manifest,cache_path=None):
 from concurrent.futures import ThreadPoolExecutor
 cache_path=cache_path or '/opt/constellation/tmp/nmpa-verified-inventory-ids.sqlite3';db=sqlite3.connect(cache_path)
 db.executescript('CREATE TABLE IF NOT EXISTS batches(task TEXT,key TEXT,sha TEXT,PRIMARY KEY(task,key));CREATE TABLE IF NOT EXISTS ids(task TEXT,id TEXT,PRIMARY KEY(task,id));')
 task=digest(manifest['task']);batches=[b for page in manifest['pages']for b in page['batches']];expected={b['key']:b['sha256']for b in batches};cached=dict(db.execute('SELECT key,sha FROM batches WHERE task=?',(task,)))
 if set(cached)-set(expected):
  with db:db.execute('DELETE FROM ids WHERE task=?',(task,));db.execute('DELETE FROM batches WHERE task=?',(task,))
  cached={}
 if any(k in cached and cached[k]!=sha for k,sha in expected.items()):db.close();raise ValueError('nmpa_inventory_batch_identity_changed')
 missing=[b for b in batches if b['key']not in cached]
 def fetch(batch):
  raw=store.get(batch['key']).body
  if hashlib.sha256(raw).hexdigest()!=batch['sha256'] or len(raw)!=batch['bytes']:raise ValueError('nmpa_cached_inventory_checksum_mismatch')
  rows=[json.loads(l)for l in raw.splitlines()]
  if len(rows)!=batch['records'] or any(r['source']!='nmpa_trials' or r['dataset']!='registry_inventory'for r in rows):raise ValueError('nmpa_cached_inventory_scope_mismatch')
  return batch,[r['source_record_id']for r in rows]
 try:
  with ThreadPoolExecutor(max_workers=4)as pool:
   for batch,ids in pool.map(fetch,missing):
    with db:
     db.executemany('INSERT OR IGNORE INTO ids VALUES (?,?)',[(task,x)for x in ids]);db.execute('INSERT OR REPLACE INTO batches VALUES (?,?,?)',(task,batch['key'],batch['sha256']))
  return {r[0]for r in db.execute('SELECT id FROM ids WHERE task=?',(task,))}
 finally:db.close()

def bounded_inventory(store,settings,universe,taxonomy,day):
 def timeout(*_):raise TimeoutError('nmpa_inventory_page_time_budget')
 previous=signal.signal(signal.SIGALRM,timeout);signal.alarm(90)
 try:return inventory(store,settings,universe,taxonomy,day,max_pages=1,seen_cache=cached_inventory_ids)
 except Exception as error:return {'status':'deferred','reason':getattr(error,'code',type(error).__name__+':'+str(error)[:100])}
 finally:signal.alarm(0);signal.signal(signal.SIGALRM,previous)

def inventory_step(store,settings,config):
 head,universe,taxonomy=inventory_context(store,config);results={}
 current=store.get(daily_head_key(universe,taxonomy));daily=json.loads(current.body)if current else{}
 page=json.loads(daily['cursor'])['page']if daily.get('cursor')else 1
 # Daily discovery gets its own attempt even if an old deep page is unavailable.
 if page<=10 and daily.get('status')!='complete' and reserve(store,config['max_provider_requests_per_day']):
  results['daily']=bounded_inventory(store,settings,universe,taxonomy,datetime.now(timezone.utc).date())
 retry=store.get(PREFIX+'/inventory-retry.json');retry=json.loads(retry.body)if retry else{}
 if head.get('status')!='complete' and retry.get('retry_after','')<=now() and reserve(store,config['max_provider_requests_per_day']):
  result=bounded_inventory(store,settings,universe,taxonomy,date.fromisoformat(head['task']['scope']['snapshot_date']));results['baseline']=result
  if result.get('status')in ('failed','deferred'):
   put_state(store,PREFIX+'/inventory-retry.json',{'reason':result.get('reason'),'retry_after':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat().replace('+00:00','Z'),'at':now()})
 return {'status':'active','results':results,'scope':'Baseline continuation plus first ten current listing pages per UTC day; not an atomic registry snapshot.'}

def prior_detail_trial(store,db,trial,prior):
 manifest=prior.get('manifest')
 if not manifest:
  saved=db.execute('SELECT manifest FROM trials WHERE registration=?',(trial[0],)).fetchone();manifest=saved[0]if saved else None
 if not manifest:return trial
 previous,_=output_rows(store,manifest);snapshot=next(r for r in previous if r['payload'].get('record_type')=='clinical_trial');parent=json.loads(trial[1]);refs=parent['payload'].setdefault('source_evidence',[])
 for ref in snapshot['payload']['source_evidence']:
  if ref not in refs:refs.append(ref)
 return (trial[0],json.dumps(parent),trial[2],json.dumps(snapshot['payload']['data']['structured']),snapshot['ingested_at'],trial[5])

def details_step(store,settings,config):
 key=PREFIX+'/progress.json';old=store.get(key);state=json.loads(old.body)if old else {'last_registration':'','processed':0,'retry_ids':[],'inventory_pages_seen':config['seed_inventory_pages'],'pending_new':[]}
 db=seed_database(config);universe=load_json(ROOT/'config/drugsfda-inventory-universe.json');taxonomy=load_json(ROOT/'config/sectors.v1.json');client=EvidenceClient(store,'nmpa_trials');out=[];started=time.monotonic()
 # Newly captured inventory IDs get priority ahead of the historical backlog.
 head,inv_universe,inv_taxonomy=inventory_context(store,config)
 for page in head['pages'][state['inventory_pages_seen']:state['inventory_pages_seen']+2]:
  for batch in page['batches']:
   raw=store.get(batch['key']).body
   if hashlib.sha256(raw).hexdigest()!=batch['sha256']:raise ValueError('nmpa_new_inventory_checksum_mismatch')
   for line in raw.splitlines():
    parent=json.loads(line);rid=parent['source_record_id']
    if not db.execute('SELECT 1 FROM trials WHERE registration=?',(rid,)).fetchone():state['pending_new'].append(parent)
  state['inventory_pages_seen']+=1
 daily=store.get(daily_head_key(inv_universe,inv_taxonomy));daily=json.loads(daily.body)if daily else{};daily_day=now()[:10];state.setdefault('daily_pages_seen',{})
 daily_seen=state['daily_pages_seen'].get(daily_day,0)
 for page in daily.get('pages',[])[daily_seen:daily_seen+2]:
  for batch in page['batches']:
   raw=store.get(batch['key']).body
   if hashlib.sha256(raw).hexdigest()!=batch['sha256']:raise ValueError('nmpa_daily_inventory_checksum_mismatch')
   for line in raw.splitlines():
    parent=json.loads(line);rid=parent['source_record_id']
    if not db.execute('SELECT 1 FROM trials WHERE registration=?',(rid,)).fetchone():state['pending_new'].append(parent)
  daily_seen+=1
 state['daily_pages_seen']={daily_day:daily_seen}
 for _ in range(4):
  if time.monotonic()-started>180:break
  kind='backlog';parent=None;cycle='baseline'
  if state['pending_new']:
   kind='new';parent=state['pending_new'][0];registration=parent['source_record_id'];trial=(registration,json.dumps(parent),parent['ingested_at'],json.dumps(None),parent['ingested_at'],0)
  else:
   due=next((r for r in state['retry_ids']if r['retry_after']<=now()),None)
   if due:
    kind='retry';registration=due['registration'];trial=db.execute('SELECT registration,parent,first_seen,baseline,baseline_at,attempts FROM trials WHERE registration=?',(registration,)).fetchone()
    if trial is None:
     parent=due['parent'];trial=(registration,json.dumps(parent),parent['ingested_at'],json.dumps(None),parent['ingested_at'],0)
   else:trial=db.execute("SELECT registration,parent,first_seen,baseline,baseline_at,attempts FROM trials WHERE status IN ('pending','retry') AND registration>? ORDER BY registration LIMIT 1",(state['last_registration'],)).fetchone()
   if not trial:
    kind='reconcile';cycle='reconcile-'+now()[:10]
    trial=db.execute('SELECT registration,parent,first_seen,baseline,baseline_at,attempts FROM trials WHERE registration>? ORDER BY registration LIMIT 1',(state.get('reconcile_cursor',''),)).fetchone()
    if not trial:state['reconcile_cursor']='';break
   registration=trial[0]
  receipt_key=PREFIX+'/trials/'+registration+'.json';prior=store.get(receipt_key);prior=json.loads(prior.body)if prior else{}
  if prior.get('status')=='captured' and (kind!='reconcile' or prior['at']>(datetime.now(timezone.utc)-timedelta(days=config['revisit_days'])).isoformat().replace('+00:00','Z')):
   if kind=='new':state['pending_new'].pop(0)
   elif kind=='backlog':state['last_registration']=registration
   elif kind=='reconcile':state['reconcile_cursor']=registration
   else:state['retry_ids']=[r for r in state['retry_ids']if r['registration']!=registration]
   continue
  if kind=='reconcile':trial=prior_detail_trial(store,db,trial,prior)
  if not reserve(store,config['max_provider_requests_per_day']):out.append({'status':'deferred_budget'});break
  try:
   def timeout(*_):raise TimeoutError('nmpa_trial_time_budget')
   old_handler=signal.signal(signal.SIGALRM,timeout);signal.alarm(90)
   try:records,refs,manifest=capture(store,settings,universe,taxonomy,config,db,client,trial,cycle)
   finally:signal.alarm(0);signal.signal(signal.SIGALRM,old_handler)
   report={'status':'captured','registration':registration,'manifest':manifest,'records':len(records),'at':now(),'capture_stage':kind}
   wid=digest(json.loads(store.get(manifest).body)['task']);report['window_id']=wid;qkey='constellation-backfill/specialist-publication-queue/nmpa-resumed/'+wid+'.json'
   if store.get(qkey)is None:write_json(store,qkey,{'window_id':wid,'manifests':[manifest],'queued_at':now(),'source':'nmpa_trials','dataset':'research_records'})
  except Exception as error:
   reason=error.code if isinstance(error,SourceIssue)else type(error).__name__+':'+str(error)[:150]
   report={'status':'retry','registration':registration,'reason':reason,'at':now(),'attempts':int(prior.get('attempts',0))+1}
   if reason=='scrape_gateway_http_429':put_state(store,receipt_key,report);out.append(report);break
   retry={'registration':registration,'retry_after':(datetime.now(timezone.utc)+timedelta(hours=24 if report['attempts']>=3 else 1)).isoformat().replace('+00:00','Z')}
   if kind=='new':retry['parent']=parent
   elif kind=='retry' and due.get('parent'):retry['parent']=due['parent']
   state['retry_ids']=[r for r in state['retry_ids']if r['registration']!=registration]+[retry]
  put_state(store,receipt_key,report);out.append(report)
  if kind=='new':
   state['pending_new'].pop(0)
  elif kind=='backlog':state['last_registration']=registration
  elif kind=='reconcile':state['reconcile_cursor']=registration
  elif report['status']=='captured':state['retry_ids']=[r for r in state['retry_ids']if r['registration']!=registration]
  if report['status']=='captured':state['processed']+=1
  state['updated_at']=now();put_state(store,key,state)
 state['updated_at']=now();put_state(store,key,state);db.close()
 return {'status':'active','results':out,'processed_since_resume':state['processed'],'retry_records':len(state['retry_ids']),'remaining_seed_trials':None,'coverage_note':'Resumes pending/retry seed trials plus new inventory IDs. No notification is sent and no completeness is inferred.'}

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=('inventory','details'));args=p.parse_args();config=load_json(ROOT/'config/nmpa-resumed-worker.json');settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store()
 with open('/opt/constellation/tmp/nmpa-resumed-'+args.mode+'.lock','a')as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  result=inventory_step(store,settings,config)if args.mode=='inventory'else details_step(store,settings,config)
  report={'mode':args.mode,'at':now(),**result};write_json(store,PREFIX+'/runs/'+args.mode+'/'+digest(report)+'.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':main()
