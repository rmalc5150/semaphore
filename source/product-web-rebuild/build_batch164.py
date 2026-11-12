from research_helpers import *
import re
records={}
for filename in ['himax-sensor-tables','himax-analogue-tables','himax-display-tables','himax-automotive-led-tables']:
 text=(out/(filename+'.txt')).read_text()
 for chunk in text.split('--------------------------------------------------------------------------------'):
  m=re.search(r'^.*?\((https://www\.himax\.com\.tw/[^)]+)\)',chunk,re.M)
  if not m:continue
  url=m.group(1);title=chunk.split(' « ')[0].strip()
  # Keep table records, excluding repeated navigation and footer links.
  category=title
  for line in re.split(r'L\d+:\s?',chunk):
   row=re.sub(r'cite[^†]*†([^]*)',r'\1',line).strip()
   if row.startswith('##### '):category=title+' — '+row.split('\n')[0].lstrip('# ')
   hit=re.match(r'((?:HX|HM|HA)\d[A-Za-z0-9]*(?:-[A-Za-z0-9]+)*(?:/[A-Za-z0-9]+)?)(?:\s*\([^)]*\))?\s*\|',row)
   if not hit:continue
   code=hit.group(1)
   records.setdefault(code,{'category':category,'urls':[]})
   if url not in records[code]['urls']:records[code]['urls'].append(url)
# Lighting uses an unformatted table. Historical date explicitly retained.
for code in ['HA6003','HA6005','HA6007','HA6207']:
 records[code]={'category':'LED lighting driver','urls':['https://www.himax.com.tw/products/other-display-related-semiconductor-solutions/lighting/']}
for code in ['HA6601','HA6602','HA6603','HA7106','HA7202','HA7207','HA7209','HA7219','HA7201','HA7203']:
 records[code]={'category':'Automotive LED driver','urls':['https://www.himax.com.tw/products/other-display-related-semiconductor-solutions/automotive/']}
records['HA5276']={'category':'OLED power management IC','urls':['https://www.himax.com.tw/products/other-display-related-semiconductor-solutions/oled/']}
products=[];evidence=[]
for code,rec in sorted(records.items()):
 es=[ev(u,'Manufacturer product table identifies this part. Repeated listings across application tables deduplicated. Catalogue listing does not establish current stock or uninterrupted production.') for u in rec['urls']]
 evidence.extend(es)
 products.append(p('Himax '+code,rec['category']+' semiconductor part listed by Himax. Current production and ordering availability unverified.',es[0],typ='product',sector='semiconductors',sub='chip_design',aliases=[code],attributes={'manufacturer_part_number':code,'catalogue_category':rec['category'],'current_availability':'unverified','variant_scope':'combined D/E catalogue entry; individual suffixes not expanded' if '/' in code else 'named catalogue part'},evidence=es))
co=company('Himax Technologies, Inc.',products,list({e['reference']:e for e in evidence}.values()),'Named parts from image-sensor, image-sensor SoC, touch-controller, operational-amplifier, PMIC, timing-controller, display-driver and LED/OLED tables reviewed. Repeated application listings deduplicated. Legacy page dates and production availability unresolved; lifecycle unknown. Need Always-On sensors, HM8030, WiseEye processors/modules/development kits, microdisplays/controllers, WLO/diffuser products, Liqxtal subsidiary attribution, complete automotive table tail, current announcements and package-variant review. Fabless developer relationship; no foundry manufacturing claim.')
(out/'batch-0164.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products));print(' '.join(records))
