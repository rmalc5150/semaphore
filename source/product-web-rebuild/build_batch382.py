from research_helpers import *
a=ev('https://www.ringfeder.com/products/elastomer-jaw-couplings/elastomer-jaw-couplings-gwe/','Nine named GWE coupling types; explicit robotics application. Bore and size variants not expanded as invented exact SKUs.')
b=ev('https://www.ringfeder.com/products/metal-bellows-couplings/','Eight named GWB coupling types for precision motion control.')
c=ev('https://www.vbggroup.com/en/media/press-releases/press-release/?slug=vbg-groups-annual-report-2025','2026 issuer statement verifies VBG parent relation to wholly owned Ringfeder division; products attributed to division rather than parent original invention.')
d=ev('https://blog.ringfeder.com/couplings-for-advanced-motion-control-systems','Company explains robotics/precision motion-control scope for GWE/GWB families.')
products=[]
for prefix,codes,src in [('GWE','5102 5103.1 5104 5106 5112 5113 5117 Z5104.1 Z5106.1',a),('GWB','AK AKD AKN CKN DKN EKN PKA Z5106',b)]:
 for code in codes.split():products.append(p('RINGFEDER '+prefix+' '+code,'Precision motion-control coupling type offered by VBG division Ringfeder.',src,life='commercial',typ='product',sector='robotics',sub='autonomy_and_components',roles=['commercial_partner'],evidence=[src,c,d]))
co=dict(company_id='cmp_2fa655fe-10e3-48b8-88da-c2521111b2c6',products=products,evidence=[a,b,c,d],status='partial',coverage_note='17 explicitly named Ringfeder GWE/GWB coupling types qualified for robotic precision motion applications; parent VBG associated through wholly owned division as commercial partner. Size/bore variants not invented. Partial: exact sizes, other directly qualified robotic coupling/brake families, Carlyle Johnson and legacy Gerwah portfolios require review. General truck couplings and vehicle HVAC not assigned robotics/storage by default.')
(out/'batch-0382.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
