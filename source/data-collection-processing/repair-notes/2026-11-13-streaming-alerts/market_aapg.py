import fcntl,json,hashlib
from datetime import date
from pathlib import Path
from urllib.request import Request,urlopen
from collection_storage import StorageSettings,write_json,now
from collection_operations import load_stored
from research_contract import ROOT,load_json,digest
from regulatory_collection import EvidenceClient
from market_operations import MarketOperations,Budget,next_month
from market_symbol_mappings import load,validate
from market_coverage_exclusions import Exclusions,report
from market_collection import collect_eodhd,enqueue
from eodhd_universe import EODHDClient
from market_athena import prepare
from window_publication import publish_pending
P=Path(__file__).parent;cfg=load_json(ROOT/'config/market-operations.json');u=load_json(ROOT/'repair-notes/2026-10-21-market-coverage/universe.json');t=load_json(ROOT/cfg['taxonomy']);settings=StorageSettings.load(ROOT/cfg['storage_config']);store=settings.store();ops=MarketOperations(store,settings,cfg,u,t)
assert ops.identity=='73d86afe67f4dc0c545538c8917092c07b4bedb8f92bc1cdb4334e66c029f886'
url='https://www.ascentage.com/ascentage-pharma-was-successfully-listed-on-nasdaq-becoming-the-first-dual-listed-18a-company-on-the-u-s-stock-market/'
with urlopen(Request(url,headers={'User-Agent':'Optima research support@optima-holdings.com'}),timeout=45)as r:raw=r.read(2*1024*1024)
assert b'January 24, 2025'in raw and b'AAPGV'in raw and b'January 27, 2025'in raw and b'AAPG'in raw
e=EvidenceClient(store,'market_coverage_review');e.save(raw,url,'text/html');proofs=e.evidence+load_json(P/'aapg-provider-probe.json')[0]['evidence'];reviewed=now();symbol='AAPGV.US';mapping=dict(symbol=symbol,target_symbol='AAPG.US',start='2025-01-27',end_exclusive=None,listing_ids=ops.symbols[symbol],explanation='Issuer confirms AAPGV when-issued ADS listing January 24, 2025 and AAPG regular-way trading from January 27; current provider returns AAPG prices through November 12, 2026. Retain exact US listing candidate, actual provider symbol and evidence on rows.',evidence=proofs,reviewer='Codex: issuer source and live budgeted provider probe',reviewed_at=reviewed);validate(mapping,symbol,ops.symbols[symbol])
with (ROOT/'.market-collection.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 key=ops.prefix+'/symbol-mappings.json';old=store.get(key);doc=json.loads(old.body)if old else {'schema_version':1,'stream_id':ops.identity,'decisions':[]};active=[x for x in doc['decisions']if x['status']=='active'and x['decision']['symbol']==symbol]
 if not active:
  write_json(store,ops.prefix+'/repairs/2026-11-13/mappings-before.json',doc);doc['decisions'].append({'id':digest(mapping),'status':'active','decision':mapping});write_json(store,ops.prefix+'/symbol-mapping-events/'+digest(mapping)+'.json',{'previous':json.loads(old.body)if old else None,'new_decision':mapping,'at':reviewed});write_json(store,key,doc,old.token if old else None)
 mapping=load(store,ops.prefix,ops.symbols)[symbol];reg=Exclusions(store,ops.prefix,ops.symbols);decision=dict(stream_id=ops.identity,source='eodhd_market',symbol=symbol,listing_ids=ops.symbols[symbol],start='2016-01-01',end_exclusive='2025-01-24',boundary_date='2025-01-24',reason='pre_ipo',explanation='Issuer confirms first US when-issued ADS listing January 24, 2025. The earlier Hong Kong listing is a distinct venue and is not substituted.',evidence=e.evidence,reviewer='Codex: issuer-confirmed US listing date',reviewed_at=reviewed);reg.add(decision);states=ops.reconcile_exclusions(reg);print(json.dumps({'stage':'reviewed_mapping_and_pre_ipo','report':report(states,reg)}),flush=True)
 client=EODHDClient.configured(load_json(ROOT/'config/eodhd-universe.json'));limits=load_json(ROOT/'config/eodhd-quota.json');client.opener=Budget(store,{'max_requests_per_day':limits['daily_group_caps']['market']},15,client.opener);ids=set();results=[]
 for lane,start,end in [('historical','2026-01-01','2026-09-01'),('daily','2026-09-01','2026-10-01'),('daily','2026-10-01','2026-11-01'),('daily','2026-11-01','2026-11-13')]:
  a,b=date.fromisoformat(start),date.fromisoformat(end);r=collect_eodhd(store,settings,u,t,symbol,a,b,lane,client,ops.symbols[symbol],symbol_mapping=mapping);results.append({'lane':lane,'start':start,'end':end,**r});print(json.dumps(results[-1]),flush=True)
  if r['status']!='complete':continue
  bound=next_month(a)if lane=='daily'else b;scope={'symbol':symbol,'universe':digest(u)};enqueue(store,r,'eodhd_market',a,bound,lane,scope);ids.add(digest({'source':'eodhd_market','start':start,'end':str(bound),'mode':lane,'scope':scope}));key=ops.prefix+'/'+lane+'.json';state,token=load_stored(store,key);item=state['symbols'][symbol];item.setdefault('gaps',{}).pop(start,None);item['scan_next_date']=max(end,item.get('scan_next_date',end));item['next_date']=min(item['gaps'])if item['gaps']else item['scan_next_date'];item.update(last_attempt=now(),last_complete=r,last_result=r,window_start=start,window_end_exclusive=end);item.pop('retry_after',None);write_json(store,key,state,token)
 write_json(store,ops.prefix+'/repairs/2026-11-13/aapg-capture-results.json',results);write_json(store,ops.prefix+'/repairs/2026-11-13/aapg-window-ids.json',sorted(ids))
 with (ROOT/'.market-athena.lock').open('a')as pub:
  fcntl.flock(pub,fcntl.LOCK_EX|fcntl.LOCK_NB);result=publish_pending(store,settings,'market',load_json(ROOT/'config/market-athena.json'),prepare,ROOT/'market-window-build',len(ids),window_ids=ids);write_json(store,ops.prefix+'/repairs/2026-11-13/aapg-publication.json',result);print(json.dumps({'stage':'athena_publication','result':result}),flush=True)
