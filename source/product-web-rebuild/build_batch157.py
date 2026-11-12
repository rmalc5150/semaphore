from research_helpers import *
a=ev('https://www.halma.com/our-companies/deep-trekker','Current parent-company portfolio identifies DeepTrekker as Halma business offering ROVs and crawlers. Parent linked as commercial partner,not the direct robot manufacturer.')
b=ev('https://www.deeptrekker.com/products/underwater-rov','Current manufacturer vehicle lineup lists SPECTRA,REVOLUTION,PIVOT,PHOTON andDTG3. Exact package contents and optional tools not assumed included.')
c=ev('https://www.deeptrekker.com/products/utility-crawlers','Current manufacturer distinguishes MAG,VAC andVACMAX utility crawlers. Base DT640 family not added again as a fourth robot.')
d=ev('https://www.deeptrekker.com/products/cctv-pipe-crawlers','Current manufacturer lists exact A150S,A150X,A200S,A200X variants. Some dimension units conflict,so disputed dimensions withheld; S/X feature differences not invented.')
e=ev('https://www.deeptrekker.com/products/underwater-rov/spectra-rov','Current SPECTRA page confirms offshore inspection ROV,not a surface vessel; product class verified directly.')
products=[]
for name in ['SPECTRA','REVOLUTION','PIVOT','PHOTON','DTG3']:
 products.append(p('Deep Trekker '+name+' ROV','Current manufacturer-listed remotely operated underwater inspection robot.',b,'commercial',roles=['commercial_partner'],typ='product',sector='robotics',sub='service_robotics',attributes={'manufacturer_brand':'Deep Trekker','model':name,'package_contents':'not_reconciled'},evidence=[a,b]+([e] if name=='SPECTRA' else [])))
for name in ['MAG','VAC','VAC MAX']:
 products.append(p('Deep Trekker '+name+' utility crawler','Current manufacturer-listed underwater utility crawler configuration.',c,'commercial',roles=['commercial_partner'],typ='product',sector='robotics',sub='service_robotics',attributes={'manufacturer_brand':'Deep Trekker','model':name},evidence=[a,c]))
for name in ['A-150S','A-150X','A-200S','A-200X']:
 products.append(p('Pipe Trekker '+name,'Current manufacturer-listed battery-operated pipe-inspection crawler variant; exact S/X equipment differences unverified.',d,'commercial',roles=['commercial_partner'],typ='product',sector='robotics',sub='service_robotics',attributes={'brand':'Pipe Trekker','manufacturer_model':name,'minimum_pipe_diameter_mm':150 if '150' in name else 200,'disputed_dimensions':'withheld'},evidence=[a,d]))
co=company('Halma plc',products,[a,b,c,d,e],'Twelve current subsidiary robot identities entered with parent commercial-partner role. No duplicate family rows on top of exact pipe variants. Conflicting dimension conversions withheld. Need all robot package/accessory/legacy variants and broader Halma portfolio including Alicat semiconductor applications,diagnostic/research instruments,biomaterials and other subsidiaries. This is a partial group scan,not completed Halma coverage.')
(out/'batch-0157.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
