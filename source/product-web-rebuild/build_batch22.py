from research_helpers import *
import re
rows=json.loads((out/'parade-reviewed-pages.json').read_text());assert len(rows)==154 and all(not r.get('error') for r in rows)
C=ev('https://www.paradetech.com/products/','All 154 linked official product pages retrieved and identity/category/description reviewed. Three pages cover two distinct models each, yielding 157 models. Suffix package variants, TrueTouch and Spectra7 legacy catalogue remain for follow-up.')
ps=[]
for r in rows:
 title=r['catalogue_title'];first=title.split()[0];desc=title[len(first):].strip();codes=[first]
 if first=='PS8580/1':codes=['PS8580','PS8581'];desc='32Gbps PCIe Gen 5 linear redriver.'
 if first in ['DP677','DP676']:
  codes=['DP677','DP678'] if first=='DP677' else ['DP676','DP679'];desc='Low power embedded DisplayPort timing controller.'
 source=ev(r['url'],'Official individual product page and matching catalogue entry support model identity and function; local HTML retained. Public model listing does not assert original invention or unlisted ordering variants.')
 for code in codes:
  assert code in r['excerpt'],code
  a={'source_catalogue':'https://www.paradetech.com/products/','source_model_designation':code}
  d=desc
  if code in ['DP677','DP678']:a['edp_lanes']=1
  if code in ['DP676','DP679']:a['edp_lanes']=2
  if code=='PS8580':a['crossbar_switch']='2x2'
  if code=='PS8581':d='32Gbps PCIe Gen 5 linear redriver without the PS8580 crossbar switch.'
  if code=='PS8762':
   d='USB-C high-speed signal-conditioning integrated circuit.';a['source_conflict']='Page/catalogue headline identifies linear redriver; duplicated body text refers to PS8802 host switch. Detailed specifications require reconciliation.'
  if code=='PS8833':
   d='USB4 and DisplayPort retimer integrated circuit.';a['source_conflict']='Page heading says Thunderbolt 3.0, body and catalogue say Thunderbolt 4. Version-specific claim omitted pending reconciliation.'
  if code=='PS8731':d='One-channel USB 3.0 redriver integrated circuit.';a['directionality']='unidirectional';a['source_conflict']='Catalogue says bidirectional; individual page explicitly says unidirectional.'
  if code=='GC2502':d='56Gbps PAM-4 / 28Gbps NRZ linear equalizer integrated circuit.';a['channels']=2
  if code in ['DP677','DP676']:pass
  if code in ['DP678','DP679']:pass
  if code in ['PS8559','PS8719','DP501']:a['design_recommendation']='not_recommended_for_new_designs'
  # Function taken from exact device listing; detailed numeric limits remain on evidence page.
  ps.append(p(code,d,source,'commercial',roles=['owner'],typ='product',sector='semiconductors',sub='integrated_circuits',attributes=a))
assert len(ps)==157 and len({p['canonical_name'] for p in ps})==157
companies=[company('PARADE TECHNOL.GDRSREGS 1',ps,[C],'All 154 linked pages in main product selection reviewed, with three explicit paired-model listings split into distinct parts. 157 named models; NRND does not imply discontinued. Unlisted suffix ordering variants, TrueTouch part inventory, Spectra7 acquisition portfolio, older discontinued devices and noted source conflicts require follow-up.')]
(out/'batch-0022.json').write_text(json.dumps({'companies':companies},indent=2))
