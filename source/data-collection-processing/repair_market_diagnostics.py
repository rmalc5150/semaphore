import json,csv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collection_storage import StorageSettings
P=Path('repair-notes/2026-10-21-market-coverage')
x=json.loads((P/'before.json').read_text());u=json.loads((P/'universe.json').read_text())
store=StorageSettings.load(Path('config/collection-storage.s3.json')).store()
items={}
for lane in ['daily','historical']:
 for symbol,v in x[lane]['symbols'].items():
  if v.get('gaps') or v.get('last_result',{}).get('status') not in ['complete','excluded']:items.setdefault(symbol,[]).append((lane,v))
def read(pair):
 symbol,lanes=pair;probes=[]
 for lane,v in lanes:
  m=v.get('last_result',{}).get('manifest')
  if m:
   o=store.get(m.rsplit('/',1)[0]+'/price-availability.json')
   if o:probes.append({'lane':lane,**json.loads(o.body)})
 return symbol,probes
probes=dict(ThreadPoolExecutor(max_workers=6).map(read,items.items()))
(P/'availability.json').write_text(json.dumps(probes,indent=2))
listings={v['listing_id']:v for v in u['listings']};companies={v['company_id']:v['canonical_name']for v in u['companies']}
rows=[]
for symbol,lanes in items.items():
 p=probes[symbol];first=min((z['provider_first_price']for z in p if z.get('provider_first_price')),default='')
 last=max((z['provider_last_price']for z in p if z.get('provider_last_price')),default='')
 category='provider_has_no_price_history' if not first else 'price_history_exists_boundary_or_mapping_review'
 for lane,v in lanes:
  gaps=dict(v.get('gaps',{}))
  if v.get('last_result',{}).get('status') not in ['complete','excluded'] and v.get('window_start'):gaps[v['window_start']]={'end_exclusive':v['window_end_exclusive']}
  for start,g in gaps.items():
   end=g['end_exclusive']
   kind=category if not first else ('before_provider_first_price_unverified' if end<=first else 'after_provider_last_price_unverified' if start>last else 'missing_inside_provider_history')
   rows.append({'symbol':symbol,'company':'; '.join(companies[listings[i]['company_id']]for i in x['listings'][symbol]),'lane':lane,'start':start,'end_exclusive':end,'classification':kind,'provider_first':first,'provider_last':last,'action':'Review listing-specific primary evidence; do not exclude on provider dates alone'})
with (P/'coverage-review.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
from collections import Counter
print('symbols',len(items),'windows',len(rows),'classification',dict(Counter(r['classification']for r in rows)))
for symbol in ['AAAP_old.US','ATLN.SW','AADI.US','1SXP.XETRA','AELIS.PA','AESGENER.SN','MMED.NEO','1CO.XETRA','1COV.XETRA']:
 r=next((r for r in rows if r['symbol']==symbol),None)
 print({k:r[k]for k in ['symbol','company','provider_first','provider_last']}if r else symbol)
