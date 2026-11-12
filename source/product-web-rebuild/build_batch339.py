from research_helpers import *
from catalogue_table_parser import Table
rows=[('TVSDiode','Transient-voltage-suppression diode.',8),('A_DiodeForAlternator','Automotive alternator diode.',18),('RoundLED','Through-hole LED.',20),('FlatLED','Flat surface-mount LED.',32),('ChipLED','Surface-mount chip LED.',38),('InfraredLED','Infrared LED.',1)]
products=[];evidence=[];review=[]
for slug,desc,expected in rows:
 src=ev('https://www.semicon.sanken-ele.co.jp/ctrl/en/product/category/'+slug+'/','Full public table names and statuses reviewed. LED preview variants retained as development, not commercial.')
 evidence.append(src);t=Table();t.feed((out/('sanken-'+slug+'-table.html')).read_text().split('|split_content|')[0]);rr=[r for r in t.rows if len(r)>3 and r[1] in ['ACTIVE','PREVIEW','NRND','DISCONTINUED']];assert len(rr)==expected
 for r in rr:
  products.append(p(r[-1],desc,src,life='commercial' if r[1]=='ACTIVE' else 'development',typ='product',sector='semiconductors',sub='chip_design',roles=['developer','manufacturer'],attributes={'manufacturer_status':r[1],'automotive_qualified':r[2],'package':r[3]}))
  review.append({'category':slug,'name':r[-1],'status':r[1]})
src=ev('https://www.semicon.sanken-ele.co.jp/ctrl/en/product/category/A_LED/','Automotive-interior LED selector has 53 rows; all already in reviewed flat/chip tables, so no duplicate product identities.')
evidence.append(src);t=Table();t.feed((out/'sanken-A_LED-table.html').read_text().split('|split_content|')[0]);rr=[r for r in t.rows if len(r)>3 and r[1] in ['ACTIVE','PREVIEW']];assert len(rr)==53
for r in rr:
 item=next(x for x in products if x['canonical_name']==r[-1]);assert item['attributes']['manufacturer_status']==r[1];item['evidence'].append(src)
assert len({x['canonical_name'] for x in products})==117
co=dict(company_id='cmp_283cd328-5e4b-448f-9b81-0d640e25abca',products=products,evidence=evidence,status='partial',coverage_note='117 additional exact diode/LED identities, including nine preview flat LEDs. Automotive selector fully reconciled: its 53 rows are already represented, not additional products. 580 current/preview parts across all 29 individual current product-category tables reviewed. Partial: standalone MCU/technical-topic products, full NRND/discontinued legacy inventory and catalogue completeness cross-check remain. Unknown electronic device numeric details omitted, product names not inferred from series patterns.')
(out/'sanken-led-reviewed-20261021.json').write_text(json.dumps(review,indent=2))
(out/'batch-0339.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
