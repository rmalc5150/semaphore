from research_helpers import *
import html,re
from collections import Counter
a=ev('https://www.sec.gov/Archives/edgar/data/1355790/000119312526131723/isco-20251231.htm','2025 issuer annual report confirms wholly owned Lifeline Cell Technology and Cyto Therapeutics. Research cells and reagents are distinct from investigational therapies and cosmetic products.')
b=ev('https://www.internationalstemcell.com/pipeline','Issuer identifies three named cellular therapeutic programmes; different indications of ISC-hpNSC do not become separate molecular products.')
c=ev('https://investors.internationalstemcell.com/International-Stem-Cell-Corporation-Announces-Successful-Completion-of-Its-Phase-1-Clinical-Trial-in-Parkinson--s-Disease-6-30-2021','Issuer confirms completed Phase 1 Parkinson study in June 2021. Stale website enrollment text does not establish a newly active trial or marketing approval.')
products=[p('ISC-hpNSC','Investigational human parthenogenetic stem-cell-derived neural stem cell preparation, with completed Phase 1 Parkinson study. Later clinical advancement unverified.',b,'development',evidence=[a,b,c]),p('ChondroStem','Investigational cartilage regeneration and tissue engineering programme; current clinical advancement unverified.',b,'research',evidence=[a,b]),p('CytoHep','Parthenogenetic stem-cell-derived hepatocyte-like cell programme for liver disease and tissue engineering; current clinical advancement unverified.',b,'research',evidence=[a,b])]
allrows=[];catalogue=[]
for page in [1,2,3]:
 rows=json.loads((out/f'lifeline-public-products-page{page}.json').read_text());allrows+=rows
 e=ev(f'https://www.lifelinecelltech.com/wp-json/wc/store/v1/products?per_page=100&page={page}','Read-only public manufacturer storefront catalogue, manually reviewed for exact product names and unique SKUs before import. Stock flag is not global lifecycle status.');e['source']='official_public_product_catalogue';e['retrieval_method']='assistant_direct_web_catalogue';catalogue.append(e)
 for x in rows:
  name=html.unescape(x['name']).replace('™','').replace('®','');name=re.sub(r'\s+',' ',name).strip()
  source=ev(x['permalink'],'Manufacturer product identity and SKU from its public storefront catalogue; donor lots and research materials are not approved therapeutic products.');source['retrieval_method']='assistant_direct_web_catalogue'
  cats=[html.unescape(y['name']) for y in x.get('categories',[])]
  products.append(p('Lifeline '+x['sku']+' '+name,'Manufacturer-catalogued cell culture research product: '+name+'. Exact catalogue SKU '+x['sku']+'.',source,'commercial',typ='product',sub='research_tools',roles=['commercial_partner'],attributes={'manufacturer_catalogue_sku':x['sku'],'manufacturer_public_product_id':x['id'],'manufacturer_categories':cats,'research_use_only':True},evidence=[a,e,source]))
assert len(allrows)==229 and len({x['id'] for x in allrows})==229 and len({x['sku'] for x in allrows})==229
co=company('International Stem Cell Corp',products,[a,b,c]+catalogue,'Reviewed three named therapeutic programmes and all 229 distinct SKU entries exposed by the current public Lifeline catalogue (three pages), with names/SKUs manually inspected. Clinical Phase 1 completion distinguished from approval; primary cells and media remain research tools. Partial: historical discontinued/removed products, donor-specific variants, proprietary parthenogenesis platform and cosmetic extract research identity remain to reconcile. Product prices, stock counts and unverified clinical claims not imported.',status='partial')
(out/'batch-0198.json').write_text(json.dumps({'companies':[co]},indent=2));print('Products staged',len(products))
