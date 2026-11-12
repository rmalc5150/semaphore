from research_helpers import *
import re
from urllib.parse import quote
data=json.loads((out/'nanoco-public-catalogue.json').read_text())['products'];assert len(data)==11
products=[];evidence=[]
for item in data:
 title=item['title'].replace('®','').strip();peak=int(re.search(r'(\d+)\s*nm',title).group(1));material='InAs' if 'InAs' in title else 'PbS'
 url='https://shop.nanocotechnologies.com/products/'+quote(item['handle'])
 e=ev(url,'Reviewed manufacturer-linked public storefront catalogue and structured variants. Amount/form options are catalogue configurations, not invented part numbers. Duplicate reported1800/2200 SKU values are not used as product identifiers.')
 evidence.append(e)
 for variant in item['variants']:
  options={o['name'].lower():variant['option'+str(o['position'])] for o in item['options']}
  amount=float(next(v for k,v in options.items() if 'amount' in k));form=next(v for k,v in options.items() if 'physical' in k)
  attrs={'material':material,'absorption_peak_nm':peak,'catalogue_amount_g':amount,'physical_form':form,'storefront_product_id':str(item['id']),'storefront_variant_id':str(variant['id']),'available_flag_at_observation':variant['available'],'source_endpoint':'https://shop.nanocotechnologies.com/products.json?limit=250'}
  if variant.get('sku'):
   if peak==2200:attrs['catalogue_sku_conflict']='2200nm listing repeats1800nm SKUs; withheld as identifier'
   else:attrs['reported_storefront_sku']=variant['sku']
  name=f'Nanoco HEATWAVE {material} {peak}nm {form} {amount:g}g'
  products.append(p(name,'Electronic-grade semiconductor quantum-dot material for infrared sensing; specified wavelength, form and amount configuration.',e,'commercial',typ='product',sector='semiconductors',sub='materials_and_packaging',roles=['manufacturer'],attributes=attrs))
assert len(products)==81
a=ev('https://www.nanocotechnologies.com/products-markets/cfqd-quantum-dots/','Current issuer identifies cadmium-free fluorescent semiconductor quantum-dot material family. End-customer TVs not company-owned products.')
b=ev('https://www.nanocotechnologies.com/full-year-trading-update-and-outlook/','August2017 issuer confirms commercial CFQD resin orders and Fine Color Film developed with Wah Hong. Current film availability unverified; partner-manufactured display films distinct from quantum-dot material.')
c=ev('https://www.nanocotechnologies.com/nanoco-awarded-grant-from-innovate-uk-for-major-life-sciences-project/','July2017 issuer identifies VIVODOTS pancreatic cancer imaging/treatment research collaboration; no current clinical approval inferred.')
products.extend([
 p('Nanoco CFQD quantum dots','Cadmium-free semiconductor quantum-dot material family for display applications. Exact size and formulation codes unresolved.',a,'commercial',typ='product',sector='semiconductors',sub='materials_and_packaging',roles=['manufacturer']),
 p('Nanoco CFQD Fine Color Film','Historical quantum-dot display film offered with Wah Hong; current availability unverified.',b,typ='product',sector='semiconductors',sub='materials_and_packaging',roles=['commercial_partner']),
 p('Nanoco VIVODOTS cancer imaging programme','Historical targeted fluorescent nanoparticle imaging/therapy research; not a verified marketed diagnostic or treatment.',c)])
co=company('Nanoco Group plc',products,list({e['reference']:e for e in evidence+[a,b,c]}.values()),'Reviewed11 direct public storefront material listings and all81 amount/form variants, plus CFQD material family,FineColorFilm and historical VIVODOTS programme. Product configurations use actual wavelength/form/amount; no duplicate family rows above81variants. 2200nm repeats1800nm SKUs in source,so conflictingSKU withheld as identifier. Need QDIR01/QDIR2/QDIR03-13 code-to-material mapping before adding potentially duplicate products, InSb variants, legacy display/lighting/biomedical programmes, precise formulation concentrations and full current availability/rights. Generic HEATWAVE brand not additional product. Partial.')
(out/'batch-0175.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products));print(products[0]['canonical_name']);print(products[-4]['canonical_name'])
