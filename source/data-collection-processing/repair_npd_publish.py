"""Publish completed manifests from this repair's logs, then verify shared batches."""
import json
from pathlib import Path
from collection_storage import StorageSettings,write_json,now
from research_contract import ROOT,load_json,digest
from research_publication import GROUPS,owner_for,prepare_for
from window_publication import publish_pending

def main():
 settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();manifests=set();news_ids=set()
 def scan(v):
  if isinstance(v,dict):
   if v.get('status')=='complete' and str(v.get('queue_key','')).startswith('operations/news/publication-queue/'):
    news_ids.add(Path(v['queue_key']).stem)
   if v.get('status')=='complete' and isinstance(v.get('manifest'),str):manifests.add(v['manifest'])
   for x in v.values():scan(x)
  elif isinstance(v,list):
   for x in v:scan(x)
 for file in (ROOT/'repair-notes/2026-10-21-news-patents-disclosures').glob('*.log'):
  if file.name.startswith(('audit','tests')):continue
  for line in file.read_text(errors='replace').splitlines():
   try:scan(json.loads(line))
   except ValueError:pass
 targets={}
 for key in sorted(manifests):
  m=json.loads(store.get(key).body);owner=owner_for(m['task'])
  if owner is None or m['status']!='complete':continue
  h=json.loads(store.get('checkpoints/'+m['task_id']+'/head.json').body)
  if h.get('terminal_manifest')!=key or h.get('status')!='complete':continue
  wid=digest(m['task']);q='operations/'+owner+'/publication-queue/'+wid+'.json';o=store.get(q)
  write_json(store,q,{'window_id':wid,'manifests':[key],'queued_at':now(),'source':m['task']['source']},o.token if o else None);targets.setdefault(owner,set()).add(wid)
 if news_ids:
  from news_athena import prepare
  result=publish_pending(store,settings,'news',load_json(ROOT/'config/news-athena.json'),prepare,ROOT/'news-window-build',max_windows=len(news_ids),window_ids=news_ids)
  print(json.dumps({'owner':'news','window_ids':sorted(news_ids),'publication':result}),flush=True)
  if result['status']=='failed':raise RuntimeError('News publication failed')
 for owner,ids in targets.items():
  filename,module=GROUPS[owner];config=load_json(ROOT/'config'/filename);config.pop('source_manifests',None)
  result=publish_pending(store,settings,owner,config,prepare_for(module),ROOT/'research-window-build'/owner,max_windows=len(ids),window_ids=ids)
  print(json.dumps({'owner':owner,'window_ids':sorted(ids),'publication':result}),flush=True)
  if result['status']=='failed':raise RuntimeError('Publication failed for '+owner)
if __name__=='__main__':main()
