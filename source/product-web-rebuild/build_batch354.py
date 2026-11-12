from research_helpers import *
a=ev('https://products.fujielectric.com/en/semiconductor/search/parametric/igbt_mod/','All 372 current-catalogue rows present in public HTML reviewed, including rows hidden by client-side pagination. Exact model codes preserved; NEW is a display badge, not part of name. Three Under development rows distinguished. Numeric electrical ratings omitted because some rows conflict with model-code expectations.')
rows=json.loads((out/'fuji-igbt-reviewed.json').read_text());products=[]
assert len(rows)==372
for r in rows:
 name=r[0].removesuffix(' NEW').removesuffix(' UP').strip()
 products.append(p(name,f'{r[4]} IGBT power module; {r[5]}.',a,life='development' if r[3]=='Under development' else 'commercial',typ='product',sector='semiconductors',sub='chip_design',roles=['developer','manufacturer']))
assert len({x['canonical_name'] for x in products})==372
co=dict(company_id='cmp_2c33c39d-0af2-4555-b8d2-808c6be581db',products=products,evidence=[a],status='partial',coverage_note='459 exact IC/sensor/module identities recorded: 87 IC and pressure-sensor grades plus all 372 rows of current IGBT-module selector. Explicit under-development badges retained; NEW badges stripped from part names. Partial: IPMs in separate selector, SiC and automotive modules, power discretes, historical products and qualifying energy-storage offerings remain. Electrical ratings with possible source inconsistencies omitted.')
(out/'batch-0354.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products),sum(x['lifecycle_status']=='development' for x in products))
