from research_helpers import *
import re
from catalogue_table_parser import Table
urls={x['id']:x['url'] for x in json.loads((out/'fuji-category-urls.json').read_text())}
config={59:('Small intelligent power module.',r'\b[67]MBP[A-Z0-9-]+'),60:('Intelligent power module.',r'\b[67]MBP[A-Z0-9-]+'),68:('Hybrid silicon/SiC power module.',r'\b2MSI[A-Z0-9-]+'),69:('All-SiC power module.',r'\b2CI[A-Z0-9-]+'),70:('Automotive IGBT power module.',r'\b6MBI[A-Z0-9-]+'),71:('Automotive SiC power module.',r'\b12CSI[A-Z0-9-]+'),73:('Discrete IGBT.',r'\bFG[WZ][A-Z0-9]+'),74:('SiC Schottky diode.',r'\bFDC[A-Z0-9]+'),75:('Automotive power MOSFET.',r'\b(?:2SK[A-Z0-9-]+|FM[BCY][A-Z0-9]+)'),76:('Automotive intelligent power switch.',r'\bF(?:50|51)[0-9]+[HL]')}
products=[];evidence=[];seen=set();counts={}
for cat,(desc,pattern) in config.items():
 src=ev(urls[cat],'Full current public catalogue table reviewed; exact model names retained. UD means under development. Package, amperage options and simulation models are not separate products.')
 evidence.append(src);t=Table();t.feed((out/f'fuji-category-{cat}.html').read_text());counts[cat]=0
 for row in t.rows:
  for cell in row:
   for match in re.finditer(pattern,cell):
    name=match.group()
    assert name not in seen,name
    seen.add(name);counts[cat]+=1
    life='development' if re.match(r'\s*UD\b',cell[match.end():]) else 'commercial'
    products.append(p(name,desc,src,life=life,typ='product',sector='semiconductors',sub='chip_design',roles=['developer','manufacturer']))
co=dict(company_id='cmp_2c33c39d-0af2-4555-b8d2-808c6be581db',products=products,evidence=evidence,status='partial',coverage_note=f'{459+len(products)} exact semiconductor identities recorded: 87 control IC/sensor models, 372 IGBT-selector rows, plus {len(products)} IPM/SiC/automotive/discrete products from ten current category tables. UD statuses preserved; package families and simulation files not products. Partial: historical semiconductor inventory, any differences versus separate parametric selectors, storage systems and other qualifying offerings remain.')
(out/'batch-0355.json').write_text(json.dumps({'companies':[co]},indent=2));print(counts,len(products),'development',sum(x['lifecycle_status']=='development' for x in products))
