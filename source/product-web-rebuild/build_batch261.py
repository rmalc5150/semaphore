from research_helpers import *
a=ev('https://www.sec.gov/Archives/edgar/data/1157602/000104746916010789/a2227568z10-k.htm','Issuer distinguishes structurally different BACE candidates and programme rights reversions. Historical clinical milestones not current activity.')
b=ev('https://www.sec.gov/Archives/edgar/data/1157602/000104746914006906/a2221051zs-1.htm','Earlier filing identifies legacy VTP-27999 and VTP-38443.')
c=ev('https://www.sec.gov/Archives/edgar/data/1578845/000119312516709205/d259988dex991.htm','Buyer announcement confirms Vitae origin of dermatology candidates and Contour platform; proposed close not assumed achieved from announcement alone.')
products=[]
for name,desc,aliases in [('VTP-43742','ROR-gamma-t inhibitor.',[]),('VTP-38543','Topical LXR-beta agonist.',[]),('VTP-36951','BACE inhibitor.',['BI 1147560']),('VTP-37948','Distinct earlier BACE inhibitor.',['BI 1181181']),('VTP-34072','11-beta-HSD1 inhibitor.',['BI187004'])]:products.append(p(name,desc,a,aliases=aliases))
for name,desc in [('VTP-38443','LXR-beta cardiovascular candidate.'),('VTP-27999','Legacy renin inhibitor.')]:products.append(p(name,desc,b))
products.append(p('Vitae Contour','Structure-based drug-discovery platform.',c,typ='technology'))
co=dict(company_id='cmp_21e261c5-0c2a-490b-b79f-cd6cace5bacf',products=products,evidence=[a,b,c],status='partial',coverage_note='Seven named historical candidates and discovery platform recorded. Distinct BACE compounds not merged; no current clinical recruitment inferred. Partial: post-Allergan/AbbVie programme disposition, subsequent codes and current licensing/termination need review. Former collaboration termination/clinical hold not automatically global discontinuation. Unknown lifecycle retained where current outcome unverified; unrelated successor portfolio not attributed to acquired Vitae.')
(out/'batch-0261.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
