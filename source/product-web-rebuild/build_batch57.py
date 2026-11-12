from research_helpers import *
import re
A=ev('https://www.kla.com/products/products-a-z','Official current A-Z catalogue retrieved directly as public HTML and reviewed by assistant; exact listed model labels and category URLs retained. No model/API discovery used. Current catalogue includes certified remanufactured systems.')
Q=ev('https://ir.kla.com/sec-filings/annual-reports/content/0000319201-26-000027/klac-20260630.htm','2026 issuer report corroborates semiconductor inspection, metrology, chemistry/process management and software categories.')
rows=json.loads((out/'kla-reviewed-index.json').read_text());ps=[];excluded=[]
for x in rows:
 n=x['name'].replace('®','').replace('™','');u=x['url']
 allowed=any(t in u for t in ['/chip-manufacturing/','/wafer-manufacturing/','/reticle-qualification','/packaging-manufacturing/','/software-solutions/semiconductor','/certified-remanufactured/','/instruments/'])
 if not allowed or n in ['8 Series','HighTemp Series','MicroSense Wafer Series','PWG5 with XT Option'] or 'zeta-solar' in u or '/nanoindenters/'in u:
  excluded.append(x);continue
 if 'defect-inspection' in u:desc='Semiconductor defect inspection or review system.'
 elif 'reticle-qualification' in u:desc='Reticle inspection or metrology system.'
 elif 'software-solutions' in u:desc='Semiconductor process-control analysis software.'
 elif 'in-situ' in u:desc='In-situ semiconductor process measurement product.'
 elif 'chemistry-process' in u:desc='Semiconductor process-chemistry measurement or control product.'
 elif '/etch' in u:desc='Semiconductor etch system configuration.'
 elif '/deposition' in u:desc='Semiconductor deposition system configuration.'
 elif 'metrology' in u or '/instruments/' in u:desc='Semiconductor surface, film or electrical measurement instrument.'
 else:desc='Semiconductor packaging inspection system.'
 names=n.split(' | ')
 if n=='Tencor P-17 & Tencor P-17 OF Stylus Profilers':names=['Tencor P-17 Stylus Profiler','Tencor P-17 OF Stylus Profiler']
 if n=='MVD300/300E':names=['MVD300','MVD300E']
 for name in names:
  attr={'catalogue_detail_url':u,'catalogue_model_label':x['name'],'evidence_scope':'official_A-Z_listing_and_link_category; full_specification_enrichment_pending'}
  if 'certified-remanufactured' in u:attr['offering_condition']='certified_remanufactured'
  if name=='PWG5':attr['catalogued_options']=['XT']
  role='developer'if'software-solutions'in u else'commercial_partner'
  ps.append(p('KLA '+name,desc,A,'commercial',roles=[role],typ='product',sector='semiconductors',sub='semiconductor_equipment',attributes=attr))
assert len({x['canonical_name']for x in ps})==len(ps)
(out/'kla-excluded-or-deferred-index.json').write_text(json.dumps(excluded,indent=2))
cs=[company('KLA Corporation',ps,[A,Q],'Exact named systems and software from current official A-Z catalogue reviewed at listed-model/category level. Shared URL does not collapse different models. PWG5 XT option retained on base model; umbrella families with explicit models skipped. Solar/HDD, general nanoindentation and PCB-only/IC-substrate relevance cases deferred. Full specification enrichment, remaining IC-substrate/OEM products, acquired-brand catalogues and historical discontinued models require followup.')]
(out/'batch-0057.json').write_text(json.dumps({'companies':cs},indent=2));print({'products':len(ps),'excluded_or_deferred':len(excluded)})
