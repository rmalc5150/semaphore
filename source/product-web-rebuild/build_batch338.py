from research_helpers import *
from catalogue_table_parser import Table
rows=[('MOSFET','Power MOSFET.',17),('IGBT','Insulated-gate bipolar transistor.',10),('Transistor','Bipolar transistor.',59),('RectifierDiode','General-purpose rectifier diode.',17),('FRD','Fast-recovery diode.',78),('HighVoltageDiode','High-voltage rectifier diode.',7),('SBD','Schottky diode.',39),('SnubberDiode','Auxiliary snubber-circuit diode.',3)]
products=[];evidence=[];review=[]
for slug,desc,expected in rows:
 src=ev('https://www.semicon.sanken-ele.co.jp/ctrl/en/product/category/'+slug+'/','All exact part names and statuses reviewed in public catalogue table. Numeric electrical specifications omitted here rather than conflating differing column definitions.')
 evidence.append(src);t=Table();t.feed((out/('sanken-'+slug+'-table.html')).read_text().split('|split_content|')[0]);rr=[r for r in t.rows if len(r)>3 and r[1] in ['ACTIVE','PREVIEW','NRND','DISCONTINUED']];assert len(rr)==expected,(slug,len(rr))
 for r in rr:
  products.append(p(r[-1],desc,src,life={'ACTIVE':'commercial','PREVIEW':'development','NRND':'unknown','DISCONTINUED':'discontinued'}[r[1]],typ='product',sector='semiconductors',sub='chip_design',roles=['developer','manufacturer'],attributes={'manufacturer_status':r[1],'automotive_qualified':r[2],'package':r[3]}))
  review.append({'category':slug,'name':r[-1],'status':r[1]})
assert len({x['canonical_name'] for x in products})==len(products)
co=dict(company_id='cmp_283cd328-5e4b-448f-9b81-0d640e25abca',products=products,evidence=evidence,status='partial',coverage_note='230 exact discrete part numbers in eight fully reviewed category tables, including two preview IGBTs. 463 exact identities recorded across 22 categories. Partial: TVS/alternator diodes, LED categories, standalone MCU offerings and NRND/discontinued inventory remain. No unsupported electrical characteristics or lifecycle claims from distributor stock.')
(out/'sanken-discrete-reviewed-20261021.json').write_text(json.dumps(review,indent=2))
(out/'batch-0338.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
