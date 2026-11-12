from research_helpers import *
O=ev('https://elengroup.com/media/Annual_Financial_Report_as_of_December_31_2025_sRe5pSU.pdf','ElEn2025annualreport confirms DEKA,Asclepion,QuantaSystem and ASA medicalbusinesses. Group-level commercialrelationship recorded without asserting each product originated inparent.')
idx=json.loads((out/'elen-reviewed-index.json').read_text());products=[]
fix={'smartxide-punto-dem':'SmartXide Punto','q-plus-evo-series':'Q-Plus EVO Series','dermablate':'Dermablate','bodylab':'BodyLab'}
for r in idx:
 slug=r['url'].rstrip('/').split('/')[-1];n=fix.get(slug,r['title'].split(' - ')[0].split(' | ')[0]);group=r['group']
 desc='Medical or aesthetic treatment system listed in the current '+group+' portfolio.'
 if n.startswith('SmartXide'):desc='CO2-based medical laser treatment system; named surgical configuration retained where separately catalogued.'
 elif n in ['Onda','Onda Plus','Onda PRO']:desc='Microwave body-contouring treatment system.'
 elif n=='Schwarzy':desc='Magnetic neuromuscular stimulation system.'
 elif n=='Dr. ARNOLD':desc='Pelvic-floor magnetic stimulation system.'
 elif n in ['Studio','SmartPICO','TORO','PicoStar','NanoStar']:desc='Laser system for dermatological pigment and tattoo treatment.'
 elif n in ['Excilite']:desc='308nm targeted phototherapy device for dermatological treatment.'
 elif n=='DenaVe':desc='585nm solid-state laser for vascular skin treatment.'
 elif n.startswith('Motus')or n.startswith('Again')or n in ['AlexStar','MeDioStar','EpiLab']:desc='Medical-aesthetic laser treatment system supporting hair removal.'
 elif n in ['Glide','DUOGlide Derma','HELIX','Tetra PRO','Tetra PRO GYN','RedTouch','RedTouch PRO','Dermablate']:desc='Laser-based tissue resurfacing or dermatological treatment system; availability and indication authorizations vary by country.'
 elif n.startswith('Fiber Dust'):desc='Thulium-fiber surgical laser for lithotripsy and soft-tissue surgery.'
 elif n.startswith('Cyber Ho')or n.startswith('Litho'):desc='Holmium surgical laser for urological treatment.'
 elif n=='Cyber TM':desc='Thulium surgical laser family.'
 elif n=='Cyber BLADE':desc='Integrated cordless disposable surgical morcellator.'
 elif n=='Opera EVO':desc='Dual-wavelength laser for soft-tissue surgery.'
 elif n=='Romeo':desc='Dermablate-compatible ErYAG treatment handpiece for snoring therapy.'
 elif n=='Juliet':desc='Dermablate-compatible ErYAG treatment handpiece system for intimate-health applications.'
 elif n=='BodyLab':desc='Functional magnetic stimulation body-treatment system.'
 elif n=='MultiPulse PRO':desc='CO2laser system for dermatology and dermatological surgery.'
 elif n=='VascuStar DYE':desc='595nm dye-laser system for dermatological treatments.'
 e=ev(r['url'],'Official individual product page reviewed along with current manufacturer catalogue. Parent linkage via ElEn2025annualreport. Accessory/model details not inferred from parent family name; marketing efficacy claims not converted into clinical conclusions.')
 products.append(p(group+' '+n,desc,e,'commercial',roles=['commercial_partner'],typ='product',attributes={'operating_brand':group,'availability_scope':'listed_in_current_official_catalogue','regulatory_authorization':'market_specific_not_inferred'},evidence=[e,O]))
cs=[company('EL.En. S.p.A',products,[O],'75distinct official product pages reviewed across DEKA42,Quanta21,Asclepion12. Parent linked as commercialpartner under documentedgroupstructure. Sharedbrands/cross-listedproducts consolidated; Romeo/Juliet identifiedas handpieces rather thanstandalonegenericlasers. Detailedfamilyvariants,accessories,consumables,ASA/JenaSurgical/legacyCynosure rightsandsemiconductor-specificindustrialproducts remain incomplete. Artconservationandgenericindustrialcuttersexcluded fromhealthcarecatalogue.')]
(out/'batch-0043.json').write_text(json.dumps({'companies':cs},indent=2));print(len(products))
