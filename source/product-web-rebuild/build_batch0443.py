import json
from pathlib import Path
from research_helpers import ev,p
cid='cmp_28727b76-9a01-4280-80b5-15c426c239c1'; src='https://www.hkexnews.hk/listedco/listconews/sehk/2025/0605/2025060500053.pdf'
products=[
 p('Electric Vehicle Battery Management Systems','Battery management systems and spare parts for electric vehicles.',src,roles=['developer','owner'],typ='technology',sector='energy_storage',sub='batteries'),
 p('Lithium-Ion Power Battery Packs and Systems','Lithium-ion power battery packs and systems for electric vehicles.',src,life='commercial',roles=['developer','owner'],typ='product',sector='energy_storage',sub='batteries',aliases=['EV battery packs']),
 p('Advanced Battery Materials','Advanced battery materials developed and sold for new-energy vehicles.',src,roles=['developer','owner'],typ='technology',sector='energy_storage',sub='batteries'),
 p('High-Tech Electric Motor Vehicles','High-tech electric motor vehicles developed and sold by Hybrid Kinetic Group.',src,roles=['developer','owner'],typ='product',sector='robotics',sub='autonomy_and_components',aliases=['electric motor vehicles']),
]
m={'batch_id':'batch-0443','companies':[{'company_id':cid,'products':products,'evidence':[ev(src,'Hybrid Kinetic Group ESG report identifies battery management systems, electric motor vehicles and advanced battery materials as principal business products.')],'status':'partial','coverage_note':'Official HKEX filing identifies the company product families; model-level vehicle names were not added without direct official evidence.'}]}
Path('/home/ec2-user/product-web-rebuild/batch-0443.json').write_text(json.dumps(m,indent=2))
