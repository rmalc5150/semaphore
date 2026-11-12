import fcntl,json
from datetime import date
from collection_storage import StorageSettings,write_json,now
from collection_operations import load_stored
from research_contract import ROOT,load_json,digest
from market_operations import MarketOperations,Budget,next_month
from market_symbol_mappings import load
from market_collection import collect_eodhd,enqueue
from eodhd_universe import EODHDClient
from window_publication import publish_pending
from market_athena import prepare
cfg=load_json(ROOT/'config/market-operations.json');u=load_json(ROOT/cfg['universe']);t=load_json(ROOT/cfg['taxonomy'])
settings=StorageSettings.load(ROOT/cfg['storage_config']);store=settings.store();ops=MarketOperations(store,settings,cfg,u,t)
with (ROOT/'.market-collection.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 mappings=load(store,ops.prefix,ops.symbols);symbol='AADI.US'
 limits=load_json(ROOT/'config/eodhd-quota.json')
 client=EODHDClient.configured(load_json(ROOT/'config/eodhd-universe.json'))
 client.opener=Budget(store,{'max_requests_per_day':limits['daily_group_caps']['market']},30,client.opener)
 ids=set();failed=False
 for lane,start,end in [('historical','2025-01-01','2026-01-01'),('historical','2026-01-01','2026-09-01'),('daily','2026-09-01','2026-10-01'),('daily','2026-10-01','2026-10-21')]:
  a,b=date.fromisoformat(start),date.fromisoformat(end)
  r=collect_eodhd(store,settings,u,t,symbol,a,b,lane,client,ops.symbols[symbol],symbol_mapping=mappings[symbol])
  print(json.dumps({'lane':lane,'start':start,'end':end,**r}),flush=True)
  if r['status']!='complete':failed=True;continue
  bound=next_month(a)if lane=='daily'else b;scope={'symbol':symbol,'universe':digest(u)}
  enqueue(store,r,'eodhd_market',a,bound,lane,scope)
  ids.add(digest({'source':'eodhd_market','start':start,'end':str(bound),'mode':lane,'scope':scope}))
  key=ops.prefix+'/'+lane+'.json';state,token=load_stored(store,key);item=state['symbols'][symbol]
  item.setdefault('gaps',{}).pop(start,None)
  item['scan_next_date']=max(end,item.get('scan_next_date',end))
  item['next_date']=min(item['gaps'])if item['gaps']else item['scan_next_date']
  item.update(last_attempt=now(),last_complete=r,last_result=r,window_start=start,window_end_exclusive=end)
  item.pop('retry_after',None);write_json(store,key,state,token)
 with (ROOT/'.market-athena.lock').open('a')as pub_lock:
  fcntl.flock(pub_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  r=publish_pending(store,settings,'market',load_json(ROOT/'config/market-athena.json'),prepare,ROOT/'market-window-build',max_windows=len(ids),window_ids=ids)
  print(json.dumps({'stage':'market_mapping_publication','window_ids':sorted(ids),'result':r}),flush=True)
  if r['status']=='failed':failed=True
raise SystemExit(2 if failed else 0)
