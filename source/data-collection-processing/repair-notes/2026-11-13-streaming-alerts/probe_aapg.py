import json
from pathlib import Path
from market_operations import Budget
from eodhd_universe import EODHDClient
from collection_storage import StorageSettings
from regulatory_collection import EvidenceClient
from research_contract import ROOT,load_json
p=Path(__file__).parent;store=StorageSettings.load(ROOT/'config/collection-storage.s3.json').store();limits=load_json(ROOT/'config/eodhd-quota.json');client=EODHDClient.configured(load_json(ROOT/'config/eodhd-universe.json'));client.opener=Budget(store,{'max_requests_per_day':limits['daily_group_caps']['market']},4,client.opener);e=EvidenceClient(store,'market_coverage_review');out=[]
for symbol in ['AAPG.US','AAPGV.US']:
 try:
  rows,raw,url=client.get('eod/'+symbol,{'from':'2025-01-24','to':'2026-11-12','order':'a'});e.evidence=[];e.save(raw,url);out.append({'symbol':symbol,'rows':len(rows),'first':rows[0]['date']if rows else None,'last':rows[-1]['date']if rows else None,'evidence':e.evidence});print(out[-1],flush=True)
 except Exception as exc:out.append({'symbol':symbol,'error':getattr(exc,'code',type(exc).__name__)});print(out[-1],flush=True)
(p/'aapg-provider-probe.json').write_text(json.dumps(out,indent=2))
