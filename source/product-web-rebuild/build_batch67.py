from research_helpers import *
import re
pages=json.loads((out/'elmos-reviewed-tables.json').read_text());ps={}
for page in pages:
 assert 'error'not in page,page
 for row in page['rows']:
  codes=re.findall(r'\bE\d{3}\.\d{2}\b',row[0]);description=re.sub(r'^(?:E\d{3}\.\d{2}[\s/,]*)+','',row[0]);description=re.sub(r'^\(\*[^)]*\)\s*','',description)
  for code in codes:
   E=ev(page['url'],'Current official category product table reviewed; exact model and source specification row retained. Cross-listing merged into the same model identity.')
   if code not in ps:ps[code]=p('Elmos '+code,description+'.',E,'commercial',typ='product',sector='semiconductors',sub='chip_design',attributes={'model':code,'official_catalogue_rows':[],'evidence_scope':'Current official catalogue offering; listing does not establish shipment volumes or every qualification option.'})
   elif E not in ps[code]['evidence']:ps[code]['evidence'].append(E)
   ps[code]['attributes']['official_catalogue_rows'].append({'source_url':page['url'],'cells':row})
# Explicit specification mappings from reviewed common table layouts.
for code,item in ps.items():
 for entry in item['attributes']['official_catalogue_rows']:
  u=entry['source_url'];r=entry['cells'];a=item['attributes']
  if u.endswith('/dcdc-converter-ic.html'):
   a.update({'output_current_as_listed':r[1],'efficiency_as_listed':r[2],'output_voltage_as_listed':r[3],'input_voltage_as_listed':r[4],'package_options_as_listed':r[5]})
  if u.endswith('/integrated-absolute-pressure-system-ic.html'):
   a.update({'interface_as_listed':r[1],'pressure_range_as_listed':r[2],'supply_voltage_as_listed':r[3],'package_options_as_listed':r[4]})
E=ev('https://www.elmos.com/english/products.html','Official product navigation followed through all public category links; generic custom ASIC design service not invented as a chip model.')
cs=[company('Elmos Semiconductor SE',list(ps.values()),[E],'All linked public product-category tables reviewed, exact E-number models deduplicated across applications and slash-separated codes preserved. Source table specifications retained; DC/DC and pressure parameters mapped. Individual datasheet availability, evaluation boards, software, QuantumRandomNumberGenerator and models not present in category tables require followup; current listing is not a shipment-volume claim.')]
(out/'batch-0067.json').write_text(json.dumps({'companies':cs},indent=2));print(len(ps));print(' '.join(ps))
