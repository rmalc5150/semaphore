from research_helpers import *
import re
from urllib.parse import quote_plus
a=ev('https://www.anipharmaceuticals.com/products.php','Entire current US catalogue manually reviewed. Exact listed medicine/formulation names retained, duplicate punctuation/USP/strength groupings consolidated. OTC icon excluded. Generic comparators are not brand aliases.')
b=ev('https://www.sec.gov/Archives/edgar/data/1023024/000102302426000014/anip-20251231.htm','Issuer confirms Cortrophin/ILUVIEN and historical YUTIQ portfolio; US promotion shifted from YUTIQ to ILUVIEN in 2025. Parent commercial role, not original development attribution.')
c=ev('https://medinfo.anipharmaceuticals.com/wp-content/uploads/2024/07/Dosing-and-Administration-of-Purified-Cortrophin%C2%AE-Gel-Repository-Corticotropin-Injection-USP-80UmL-in-Patients-With-Keratitis-1.pdf','Porcine-derived ACTH repository corticotropin identity confirmed. No dose recommendations copied.')
def norm(s):return re.sub(r'[^a-z0-9]','',s.lower().replace('usp',''))
groups={}
for r in json.loads((out/'ani-reviewed-catalogue.json').read_text()):
 if r['id']==165 or r['name']=='L-Methylfolate Calcium Tablets':continue
 groups.setdefault(norm(r['name']),[]).append(r)
products=[]
for rows in groups.values():
 original=rows[0]['name'];name=original.replace('®','').replace('™','').split('(')[0].strip() if any(x in original for x in ['®','™']) else original
 products.append(p(name,original.replace('®','').replace('™','')+'; U.S. portfolio formulation.',a,life='commercial',typ='product',roles=['commercial_partner'],territory='US'))
products.extend([p('Purified Cortrophin Gel','Porcine-derived repository corticotropin injection.',c,life='commercial',typ='product',roles=['commercial_partner'],territory='US',evidence=[b,c]),p('ILUVIEN','Fluocinolone acetonide intravitreal implant.',b,life='commercial',typ='product',roles=['commercial_partner'],territory='US'),p('YUTIQ','Historical fluocinolone acetonide intravitreal implant; U.S. promotion shifted to ILUVIEN in 2025.',b,typ='product',roles=['commercial_partner'],territory='US')])
assert len({x['canonical_name'].lower() for x in products})==len(products)
co=dict(company_id='cmp_2c47196a-9863-4501-9aff-737b1072b412',products=products,evidence=[a,b,c],status='partial',coverage_note=f'{len(products)} medicine/formulation families from full public US catalogue plus Cortrophin/ILUVIEN/historical YUTIQ. Duplicate strength/punctuation/USP groupings consolidated; no pack-size SKU inflation. Commercial-partner role restricted to US; manufacturing/development and worldwide rights not inferred. YUTIQ current lifecycle unknown, promotion transferred to ILUVIEN. L-methylfolate medical-food qualification unresolved and excluded. Partial: individual NDC/strength metadata, detailed approved indications, non-US/historical/divested brands and development pipeline remain.')
(out/'batch-0361.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
