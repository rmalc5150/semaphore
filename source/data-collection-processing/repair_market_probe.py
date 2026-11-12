import json
from market_operations import Budget
from eodhd_universe import EODHDClient
from collection_storage import StorageSettings
from regulatory_collection import EvidenceClient
from research_contract import ROOT,load_json
settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store()
limits=load_json(ROOT/'config/eodhd-quota.json')
client=EODHDClient.configured(load_json(ROOT/'config/eodhd-universe.json'))
client.opener=Budget(store,{'max_requests_per_day':limits['daily_group_caps']['market']},8,client.opener)
e=EvidenceClient(store,'market_coverage_review')
for symbol in ['WHWK.US','AADI.US','AESANDES.SN']:
 for kind in ['fundamentals','eod']:
  params={'filter':'General'} if kind=='fundamentals' else {'from':'2025-03-19','to':'2026-10-20','order':'a'}
  try:
   rows,raw,url=client.get(kind+'/'+symbol,params);e.evidence=[];e.save(raw,url)
   if kind=='fundamentals':summary={k:rows.get(k)for k in ['Code','Name','Exchange','ISIN','CUSIP','CIK','IPODate','DelistedDate','IsDelisted']}
   else:summary={'rows':len(rows),'first':rows[0]['date']if rows else None,'last':rows[-1]['date']if rows else None}
   print(json.dumps({'symbol':symbol,'kind':kind,'summary':summary,'evidence':e.evidence}),flush=True)
  except Exception as exc: print(json.dumps({'symbol':symbol,'kind':kind,'error':getattr(exc,'code',type(exc).__name__)}),flush=True)
