from research_helpers import *
r=json.loads((out/'batch-0004.receipt.json').read_text())
old=next(c for c in r['manifest']['companies'] if any(p['canonical_name']=='Sirexatamab' for p in c['products']))
a=ev('https://www.sec.gov/Archives/edgar/data/1509745/000110465926028566/cyph-20251231x10k.htm','Issuer confirms parent formerly Leap Therapeutics renamed Cypherpunk in November 2025, new wholly-owned Leap subsidiary holds ongoing biotech operations. Identifies sirexatamab/FL-501 and legacy TRX518/FL-301/FL-302 expenditures.')
b=ev('https://www.cypherpunk.com/investors/releases/cypherpunk-technologies-reports-second-quarter-2026-financial','August 2026 issuer confirms continued strategic process for sirexatamab; Phase 3 alignment not actual initiation.')
products=old['products']
for item in products:
 item['product_id']=item.pop('inserted_product_id')
 item['evidence'] += [a,b] if item['canonical_name']=='Sirexatamab' else [a]
co=dict(company_id='cmp_0cc1b186-e35f-4ce0-9ecd-5e889525da70',products=products,evidence=[a,b]+old['evidence'],status='partial',coverage_note='Five existing Leap therapeutic identities shared with renamed Cypherpunk parent; no duplicate products created. Historical developer association retained, new wholly-owned Leap subsidiary distinguished from parent rename. Partial: current FL-501 funding/status, legacy TRX518/FL-301/FL-302 rights and proposed biotech spinout/partner transaction remain. Cryptocurrency mining and treasury assets not semiconductor or energy storage products.')
(out/'batch-0234.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
