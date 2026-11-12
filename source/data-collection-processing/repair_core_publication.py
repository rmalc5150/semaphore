"""Publish the repaired core windows, then refresh shared Athena access."""
import json,subprocess,sys
from datetime import datetime,timezone
from collection_storage import StorageSettings,write_json,now
from research_contract import ROOT,load_json,digest
from research_publication import GROUPS,owner_for,prepare_for
from window_publication import publish_pending

def main():
 settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store()
 targets={};after=datetime(2026,10,21,17,tzinfo=timezone.utc)
 for source in ('uk_mhra','ema_ctis','hkex_news','uspto_odp'):
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
 key='operations/repairs/2026-10-21/core-publications.json'
 prior=store.get(key)
 write_json(store,key,report,prior.token if prior else None)

 return int(any(v.get('status')=='failed' for v in report['publications'].values()))

if __name__=='__main__':raise SystemExit(main())
