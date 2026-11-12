from research_helpers import *
import re
idx=json.loads((out/'cooper-reviewed-index.json').read_text());ps=[];es={};seen=set()
selected={'RI Witness™ System','The Stripper™ Pipettor and Tips','EZ-Range™ Pipettors and Tips','PICSI® dish for sperm selection','GPS Dishware','ERBiome℠ Test','ER-Peak℠ Test','ER-Complete℠ Test','PGTai℠ Technology Platform','PGT-SR','PGT-M','PGT-A','PGT-COMPLETE℠ TEST','RI Witness IQ™ Solution','Scanfuge Centrifuges','K-Systems™ AV1 Anti Vibration Table','K-Systems™ Warming Blocks','RI Integra 3™ Micromanipulator','RI Saturn 5™ Active laser system','CodaAir® Positive Pressure System','ORIGIO® Gas Line Filter','Coda® Xtra Inline® Filters','CodaAir® Incubator Units','L126 IVF Workstation','Fortuna-IVF Workstation','Titan-IVF Workstation','Mars-IVF Class II Workstation'}
for x in idx:
 page=int(re.search(r'/page/(\d+)/',x['source'])[1]);n=x['name']
 if not(3<=page<=8 or n in selected):continue
 if n in ['Culture Media with GM-CSF','Assisted Hatching and Zona Dissection Micropipettes','Intracytoplasmic Sperm Injection (ICSI) Pipettes']:continue
 n=n.translate(str.maketrans('','','®™℠')).strip()
 if n in seen:continue
 seen.add(n)
 s=es.setdefault(x['source'],ev(x['source'],'Manufacturer regional catalogue reviewed for named offerings; family entries retained as families, not expanded into undocumented codes. Countryavailability varies.'))
 sub='diagnostics' if n.startswith(('ERBiome','ER-Peak','ER-Complete','PGT-')) or n=='HBA Assay' else 'research_tools'
 typ='technology' if n.startswith(('RI Witness','PGTai')) else 'product'
 desc='IVF laboratory medium, reagent or consumable.' if 3<=page<=8 else 'Named fertility laboratory product or system.'
 if sub=='diagnostics':desc='Reproductive diagnostic test.'
 ps.append(p('CooperSurgical '+n,desc,s,'commercial',roles=['commercial_partner'],typ=typ,sub=sub,attributes={'identity_scope':'named catalogue offering/family; individual ordering variants require detail review'}))
G=ev('https://www.coopersurgical.com/product/culture-media-with-gm-csf/','Official page names three separate GMCSF culture media; umbrella page not a fourth product.')
for n in ['SAGE 1-Step GM-CSF','EmbryoGen','BlastGen']:ps.append(p('CooperSurgical '+n,'GM-CSF-supplemented IVF culture medium.',G,'commercial',roles=['commercial_partner'],typ='product',sub='research_tools'))
P=ev('https://www.coopercos.com/coopersurgical/','Current parent confirms CooperSurgical business relationship.')
cs=[company('The Cooper Companies, Inc',ps,list(es.values())+[G,P],'Reviewed worldwide archive pages2-16 for IVF media, diagnostics and named laboratory systems. Informational RIWitness subpages deduplicated; generic microscope/tool categories and ordinary manual surgical devices deferred rather than assumed proprietary biotechnology/robotics. GMCSF umbrella replaced by3 actual media. Page1 unavailable; individual product codes, latest availability, ZyMot, broader medical offerings, CooperVision and other regional catalogues remain to research.')]
(out/'batch-0087.json').write_text(json.dumps({'companies':cs},indent=2));print(len(ps))
