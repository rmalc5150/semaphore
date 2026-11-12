"""Replay one saved specialist scope and verify its normal Athena publication."""
import argparse,json
from research_contract import ROOT,load_json,digest
from collection_storage import StorageSettings,write_json,now
from specialist_inputs import collect,VERSION,discover_children
from specialist_publication import publish

def save_report(store, identity, report):
 key='operations/repairs/2026-10-21/'+identity+'.json'
 previous=store.get(key)
 if previous:
  old=json.loads(previous.body)
  write_json(store,'operations/repairs/2026-10-21/attempts/'+identity+'/'+digest(old)+'.json',old)
 write_json(store,'operations/repairs/2026-10-21/attempts/'+identity+'/'+digest(report)+'.json',report)
 write_json(store,key,report,previous.token if previous else None)

def main():
 p=argparse.ArgumentParser();p.add_argument('lane');p.add_argument('source');p.add_argument('--reason');p.add_argument('--pages',type=int,default=4);a=p.parse_args()
 settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store()
 key='operations/specialists/scheduler/'+a.lane+'.json';obj=store.get(key);state=json.loads(obj.body)
 matches=[(k,r) for k,r in state['jobs'].items() if r.get('source')==a.source and r.get('status') in ('failed','partial') and (not a.reason or a.reason in r.get('reason',''))]
 if not matches: print(json.dumps({'source':a.source,'status':'no_matching_failed_scope'}));return
 identity,prior=sorted(matches,key=lambda x:x[1].get('last_attempt',''),reverse=True)[0]
 legacy_identity=None
 job=prior.get('job')
 if job is None:
  task=json.loads(store.get(prior['manifest']).body)['task']
  job={**task['scope'],'source':task['source'],'mode':task['mode'],
       'start':task['window']['start'][:10],'end':task['window']['end'][:10]}
  if digest({'job':job,'universe_hash':task['universe_hash'],'version':task['collector_version']})!=identity:
   raise ValueError('Legacy scope reconstruction failed identity verification')
  legacy_identity=identity
 universe=load_json(ROOT/'config/company-universe.v0.5.json');taxonomy=load_json(ROOT/'config/sectors.v1.json')
 expected=digest({'job':job,'universe_hash':digest(universe),'version':VERSION})
 if legacy_identity:
  if task['universe_hash']!=digest(universe):raise ValueError('Legacy universe changed; mapping review required')
  identity=expected
 elif expected!=identity: raise ValueError('Scope universe/version changed; explicit migration required')
 print(json.dumps({'stage':'repair_scope_started','source':a.source,'job_id':identity,'job':job}),flush=True)
 result=collect(job,store,settings,universe,taxonomy,a.pages)
 state['jobs'][identity]={**result,'job_id':identity,'source':a.source,'source_id':job['source_id'],'start':job['start'],'end_exclusive':job['end'],'last_attempt':now(),'job':job}
 state['updated_at']=now();write_json(store,key,state,obj.token)
 report={'at':now(),'job_id':identity,'legacy_job_id':legacy_identity,'prior_manifest':prior.get('manifest'),'capture':result}
 print(json.dumps(report),flush=True)
 if result['status'] in {'complete','partial'} and result.get('records',0):
  discover_children(store,result['manifest'],job)
 if result['status']=='complete':
  q='operations/specialists/publication-queue/'+identity+'.json';existing=store.get(q)
  write_json(store,q,{'window_id':identity,'manifests':[result['manifest']],'queued_at':now()},existing.token if existing else None)
  report['publication']=publish(store,settings,load_json(ROOT/'config/specialist-inputs.json'),1,[identity])
  if legacy_identity and any(r.get('window_id')==identity and r.get('status')=='verified' for r in report['publication']['results']):
   latest=store.get(key); updated=json.loads(latest.body)
   updated['jobs'][legacy_identity]={**prior,'status':'superseded','replacement_job_id':identity,
     'reason':'verified_collector_version_migration','reconciled_at':now()}
   write_json(store,key,updated,latest.token)
 save_report(store,identity,report)
 print(json.dumps(report),flush=True)
 if result['status'] not in {'complete','partial','paused_by_user'}:return 1
 if result['status']=='complete':
  receipt_obj=store.get('operations/specialists/publication-receipts/'+identity+'.json')
  receipt=json.loads(receipt_obj.body) if receipt_obj else {}
  if receipt.get('status')!='verified' or result['manifest'] not in receipt.get('manifests',[]):return 1
 return 0
if __name__=='__main__':raise SystemExit(main())
