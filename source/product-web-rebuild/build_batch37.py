from research_helpers import *
import re
from html import unescape
from html.parser import HTMLParser
R=ev('https://www.sanofi.us/en/your-health/products/prescription-products','Official current US prescription catalogue; distinct formulations retained, strengths grouped within listed product. Listing supports US commercial relationship, not original invention.')
V=ev('https://www.sanofi.us/en/your-health/products/vaccine-products','Official US immunization catalogue, also includes Beyfortus antibody and Tubersol diagnostic reagent. Archived product entries independently checked where discontinuation known.')
D=ev('https://www.cdc.gov/acip/downloads/slides-2024-06-26-28/01-Denvaxia-Bergren-508.pdf','Sanofi presentation to CDC ACIP: Dengvaxia discontinued due to low demand, last doses expire August2026. Overrides stale US product listing.')
P=ev('https://www.sanofi.com/en/our-science/our-pipeline','Official July30 2026 clinical pipeline reviewed, 61 projects consolidated by underlying asset; indication expansions not treated as new medicines. SP0287 has two explicitly different vaccine formulations.')
products=[]
for kind,e in [('rx',R),('vaccines',V)]:
 s=(out/f'sanofi-{kind}.html').read_text()
 for h in re.findall(r'<h3[^>]*>(.*?)</h3>',s,re.S):
  h=unescape(re.sub('<[^>]+>','',h)).strip();h=re.sub('[®™]','',h)
  if not h:continue
  name=re.split(r'\s*[\(\[]',h)[0].strip()
  if name.startswith('Merilog'):name='Merilog'
  if name.startswith('Arava'):name='Arava'
  if name.startswith('Renagel'):name='Renagel'
  if name.startswith('Priftin'):name='Priftin'
  item=p(name,h,e,'discontinued' if name=='Dengvaxia' else 'commercial',roles=['commercial_partner'],typ='product',territory='USA',sub='diagnostics' if name=='TUBERSOL' else 'therapeutics')
  if name=='Dengvaxia':item['evidence'].append(D)
  # Same underlying branded product already linked to regional licensee CStone.
  if name.lower()=='ayvakit':
   prior=json.loads((out/'batch-0027.receipt.json').read_text())['manifest']['companies'][0]['products'];item['product_id']=next(x['inserted_product_id'] for x in prior if x['canonical_name']=='AYVAKIT')
  products.append(item)
class T(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.x=[]
 def handle_starttag(self,t,a):
  if t in ['style','script']:self.skip+=1
 def handle_endtag(self,t):
  if t in ['style','script']:self.skip-=1
 def handle_data(self,d):
  if not self.skip and d.strip():self.x.append(d.strip())
t=T();t.feed((out/'sanofi-pipeline.html').read_text());x=t.x
names={p['canonical_name'].lower():p for p in products};names['fitusiran']=names['qfitlia'];names['fluzone hd']=names['fluzone high dose']
for i,a in enumerate(x):
 if a!='Name' or i+2>=len(x) or x[i+2]!='Phase':continue
 z=x[i:i+45];name=x[i+1];di=z.index('Description');ii=z.index('Indication');desc=z[di+1];ind=z[ii+1]
 if ',' in name:continue # Multi-agent exploratory listing not evidence of a single fixed-combination product.
 if name=='SP0287':name+=' (Flublok + Nuvaxovid)' if desc=='Flublok+Nuvaxovid' else ' (Fluzone HD + Nuvaxovid)'
 if name=='Sarclisa' and 'subcutaneous' in desc:name='Sarclisa subcutaneous formulation'
 item=names.get(name.lower())
 if item is None:
  item=p(name,desc,P,'development',roles=['developer']);products.append(item);names[name.lower()]=item
 item.setdefault('contexts',[]).append({'application_key':re.sub('[^a-z0-9]+','_',ind.lower()).strip('_'),'application_name':ind,'geography_key':'unknown','development_stage':'clinical_development','regulatory_status':'investigational_indication'})
 if P not in item['evidence']:item['evidence'].append(P)
for n,alias in [('WAYRILZ','rilzabrutinib'),('Qfitlia','fitusiran')]:
 item=names[n.lower()];item['aliases'].append({'alias':alias,'alias_type':'generic_name'})
cs=[company('Sanofi',products,[R,V,D,P],'US prescription and immunization catalogues plus July2026 clinical pipeline reviewed. AYVAKIT reused from existing shared product rather than duplicated; Sanofi link US commercial partner only. Dengvaxia discontinued per Sanofi ACIP presentation despite stale catalogue listing. Remaining international brands, Winthrop generics, legacy/divested assets, acquired Blueprint/Vigil portfolios and detailed rights/aliases require follow-up. No claim of worldwide catalogue completion.')]
(out/'batch-0037.json').write_text(json.dumps({'companies':cs},indent=2));print(len(products))
