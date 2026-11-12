"""Publish the repaired core windows, then refresh shared Athena access."""
import json,subprocess,sys
from datetime import datetime,timezone
from collection_storage import StorageSettings,write_json,now
from research_contract import ROOT,load_json,digest
from research_publication import GROUPS,owner_for,prepare_for
from window_publication import publish_pending

def main():
 subprocess.run([sys.executable,'-B','people_social_collection.py','--social-only'],cwd=ROOT,check=False)
 subprocess.run([sys.executable,'-B','reddit_collection.py'],cwd=ROOT,check=False)
 for args in [
  ['daily','github_sdk','--reason','source_http_422','--pages','2'],
  ['daily','uspto_assignment_histories','--reason','No space left','--pages','2'],
  ['authenticated-historical','eia_retail_prices','--reason','source_http_504','--pages','4'],
  ['authenticated-historical','sam_gov_opportunities','--reason','No space left','--pages','1']]:
  result=subprocess.run(['/usr/bin/timeout','--signal=INT','--kill-after=120s','600',sys.executable,'-B','repair_scope.py',*args],cwd=ROOT)
  print(json.dumps({'stage':'remaining_scope_replay','arguments':args,'exit_code':result.returncode}),flush=True)
 settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store()
 targets={};after=datetime(2026,10,21,17,tzinfo=timezone.utc)
 for source in ('uk_mhra','ema_ctis','bluesky_search','hkex_news','uspto_odp'):
  prefix=settings.s3_prefix+'/manifests/collection_runs/source='+source+'/'
  for page in store.client.get_paginator('list_objects_v2').paginate(Bucket=settings.s3_bucket,Prefix=prefix):
   for obj in page.get('Contents',[]):
    if obj['LastModified']<after or not obj['Key'].endswith('/final.json'):continue
    key=obj['Key'].removeprefix(settings.s3_prefix+'/');m=json.loads(store.get(key).body)
    if m.get('status')!='complete':continue
    owner=owner_for(m['task'])
    if owner is None:continue
    head=json.loads(store.get('checkpoints/'+m['task_id']+'/head.json').body)
    if head.get('status')!='complete' or head.get('terminal_manifest')!=key:continue
    wid=digest(m['task']);q='operations/'+owner+'/publication-queue/'+wid+'.json';saved=store.get(q)
    write_json(store,q,{'window_id':wid,'manifests':[key],'queued_at':now(),'source':source},saved.token if saved else None)
    targets.setdefault(owner,set()).add(wid)
 report={'started_at':now(),'targets':{o:sorted(v) for o,v in targets.items()},'publications':{}}
 for owner,ids in targets.items():
  filename,module=GROUPS[owner];config=load_json(ROOT/'config'/filename);config.pop('source_manifests',None)
  report['publications'][owner]=publish_pending(store,settings,owner,config,prepare_for(module),ROOT/'research-window-build'/owner,24,ids)
  print(json.dumps({'owner':owner,'publication':report['publications'][owner]}),flush=True)
 write_json(store,'operations/repairs/2026-10-21/core-publications.json',report)
 for command,timeout in [(['readiness_recurring.py'],600),(['committed_data_athena.py'],1800)]:
  print(json.dumps({'stage':'verification_started','command':command}),flush=True)
  result=subprocess.run(['/usr/bin/timeout','--signal=INT','--kill-after=120s',str(timeout),sys.executable,'-B',*command],cwd=ROOT)
  print(json.dumps({'stage':'verification_finished','command':command,'exit_code':result.returncode}),flush=True)
if __name__=='__main__':main()
