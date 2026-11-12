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
plans=[('1CO.XETRA','post_delisting','2026-01-01','2027-01-01','2025-12-06','Official Xetra deletion notice: tendered Covestro shares ISIN DE000A40KY26 last traded December 5, 2025. Different security from 1COV. Conservative 2026-only exclusion.'),('1COV.XETRA','documented_unavailable','2026-01-01','2027-01-01','2025-12-23','Issuer annual report confirms ordinary-share Xetra trading ended December 22, 2025; Frankfurt trading continues. Provider has December 23 price: preserve discrepancy and exclude only 2026, not that record. No cross-venue substitution.')]
decisions=[dict(stream_id=ops.identity,source='eodhd_market',symbol=s,listing_ids=ops.symbols[s],start=a,end_exclusive=b,boundary_date=c,reason=r,explanation=e,evidence=proofs[s],reviewer='Codex: primary-source review requested by account owner',reviewed_at=reviewed)for s,r,a,b,c,e in plans]
with (ROOT/'.market-collection.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 reg=Exclusions(store,ops.prefix,ops.symbols)
 (P/'registry-before-covestro.json').write_text(json.dumps(reg.document,indent=2))
 for d in decisions:print(json.dumps({'excluded_decision':reg.add(d),'symbol':d['symbol']}))

 states=ops.reconcile_exclusions(reg)
 result=report(states,reg);(P/'final-coverage.json').write_text(json.dumps(result,indent=2))
 (P/'covestro-decisions.json').write_text(json.dumps(decisions,indent=2))
 print(json.dumps({'lanes':{k:{'unresolved_symbols':v['unresolved_symbols'],'excluded_windows':len(v['excluded_windows'])}for k,v in result['lanes'].items()}}))
