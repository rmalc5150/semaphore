from research_helpers import *
a=ev('https://www.sec.gov/Archives/edgar/data/1836379/000162828022008655/vectivbiocorporatepresen.htm','Issuer explicitly names four Comet candidates and modular platform; planned trial dates not treated as achieved.')
b=ev('https://ironwoodpharma.com/science-medicine/pipeline/','Successor confirms completed VectivBio acquisition June 2023 and apraglutide lineage.')
c=ev('https://investor.ironwoodpharma.com/press-releases/press-release-details/2026/Ironwood-Pharmaceuticals-Raises-2026-Full-Year-Financial-Guidance-Building-on-Strong-Second-Quarter-Results/default.aspx','August 2026 successor update confirms initiated, recruiting confirmatory STARS-2 apraglutide Phase 3 study.')
products=[p('Apraglutide','Investigational long-acting GLP-2 analogue for short bowel syndrome.',b,'development',evidence=[b,c])]
for code,desc in [('VB-1197','Organic-acidaemia candidate.'),('VB-1200','Urea-cycle-disorder candidate.'),('VB-1300','Fatty-acid-oxidation-disorder candidate.'),('VB-1400','Amino-acidopathy candidate.')]:
 products.append(p(code,desc,a))
products.append(p('VectivBio Comet platform','Modular stabilized-pantetheine chemistry for inherited metabolic diseases.',a,typ='technology'))
co=dict(company_id='cmp_1a77e3c7-f9e8-4f67-899a-a63951fa86d0',products=products,evidence=[a,b,c],status='partial',coverage_note='Apraglutide plus four coded legacy Comet candidates and distinct chemistry platform recorded. Apraglutide multiple indications grouped. Partial: current Comet ownership/development, exact VectivBio subsidiary rights after Ironwood transaction and legacy aliases need review. No attribution of unrelated parent Linzess to acquired VectivBio. Legacy Comet lifecycle unknown rather than extrapolating planned 2023 first-in-human trial.')
(out/'batch-0252.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
