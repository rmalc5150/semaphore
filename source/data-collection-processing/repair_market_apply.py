import fcntl,json,hashlib
from pathlib import Path
from collection_storage import StorageSettings,write_json,now
from research_contract import ROOT,load_json,digest
from market_operations import MarketOperations
from market_coverage_exclusions import Exclusions,report
from market_symbol_mappings import validate,load
P=ROOT/'repair-notes/2026-10-21-market-coverage'
cfg=load_json(ROOT/'config/market-operations.json');u=load_json(P/'universe.json')
settings=StorageSettings.load(ROOT/cfg['storage_config']);store=settings.store()
ops=MarketOperations(store,settings,cfg,u,load_json(ROOT/cfg['taxonomy']))
proofs=load_json(P/'primary-evidence.json');reviewed=now()
plans=[
 ('AELIS.PA','pre_ipo','2021-01-01','2022-02-18','2022-02-18','Euronext confirms the first trading day on February 18, 2022. Applies only to the Paris listing.'),
 ('1SXP.XETRA','pre_ipo','2021-01-01','2023-09-28','2023-09-28','Deutsche Boerse identifies SCHOTT Pharma ISIN DE000A3ENQ51 and first trading day September 28, 2023.'),
 ('MMED.NEO','post_delisting','2024-04-11','2027-01-01','2024-04-11','Issuer SEC exhibit confirms Cboe Canada delisting at close April 10, 2024. Nasdaq MNMD is a different venue/currency and is not substituted. Review horizon ends January 1, 2027.'),
 ('ATLN.SW','post_delisting','2021-01-01','2027-01-01','2017-11-07','Depositary notice confirms SIX last trading November 6, 2017 and delisting November 7. Applies only to the Actelion listing, not Johnson & Johnson. Review horizon ends January 1, 2027.')]
decisions=[dict(stream_id=ops.identity,source='eodhd_market',symbol=s,listing_ids=ops.symbols[s],start=a,end_exclusive=b,boundary_date=c,reason=r,explanation=e,evidence=proofs[s],reviewer='Codex: primary-source review requested by account owner',reviewed_at=reviewed)for s,r,a,b,c,e in plans]
mapping={'symbol':'AADI.US','target_symbol':'WHWK.US','start':'2025-03-19','end_exclusive':None,'listing_ids':ops.symbols['AADI.US'],'explanation':'SEC issuer release confirms the same public company common stock changes name/ticker to Whitehawk/WHWK on March 19, 2025. Keep the pinned listing candidate and disclose actual provider symbol on each row.','evidence':proofs['AADI.US'],'reviewer':'Codex: issuer filing and live provider probe','reviewed_at':reviewed}
validate(mapping,'AADI.US',ops.symbols['AADI.US'])
for d in decisions+[mapping]:
 for p in d['evidence']:
  o=store.get(p['key']);assert o and hashlib.sha256(o.body).hexdigest()==p['sha256']
with (ROOT/'.market-collection.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 reg=Exclusions(store,ops.prefix,ops.symbols)
 (P/'registry-before-apply.json').write_text(json.dumps(reg.document,indent=2))
 for d in decisions:print(json.dumps({'excluded_decision':reg.add(d),'symbol':d['symbol']}))
 key=ops.prefix+'/symbol-mappings.json';old=store.get(key)
 doc=json.loads(old.body) if old else {'schema_version':1,'stream_id':ops.identity,'decisions':[]}
 if any(v['status']=='active' and v['decision']['symbol']=='AADI.US' for v in doc['decisions']):raise RuntimeError('Existing mapping requires review')
 doc['decisions'].append({'id':digest(mapping),'status':'active','decision':mapping})
 write_json(store,ops.prefix+'/symbol-mapping-events/'+digest(mapping)+'.json',{'previous':json.loads(old.body)if old else None,'new_decision':mapping,'at':reviewed})
 write_json(store,key,doc,old.token if old else None)
 assert load(store,ops.prefix,ops.symbols)['AADI.US']==mapping
 states=ops.reconcile_exclusions(reg)
 result=report(states,reg);(P/'applied-coverage.json').write_text(json.dumps(result,indent=2))
 (P/'decisions.json').write_text(json.dumps(decisions,indent=2));(P/'mapping.json').write_text(json.dumps(mapping,indent=2))
 print(json.dumps({'lanes':{k:{'unresolved_symbols':v['unresolved_symbols'],'excluded_windows':len(v['excluded_windows'])}for k,v in result['lanes'].items()}}))
