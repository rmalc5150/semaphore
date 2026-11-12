import json
from pathlib import Path
from research_helpers import ev,p
cid='cmp_29cd206f-e88a-4cd2-b7a8-dbf13eeb0828'; mob='https://www.toyota-tsusho.com/english/company/business/mobility.html'; dig='https://www.toyota-tsusho.com/english/company/business/digital-solutions.html'; met='https://www.toyota-tsusho.com/english/company/business/metal.html'; life='https://www.toyota-tsusho.com/english/company/business/lifestyle.html'
products=[
 p('Toyota and Lexus Vehicles','Toyota Tsusho vehicle import, assembly, wholesale and retail business covering Toyota vehicles.',mob,roles=['commercial_partner'],typ='product',sector='robotics',sub='autonomy_and_components',aliases=['Toyota vehicles']),
 p('Commercial and Industrial Vehicles','Commercial, passenger and industrial vehicle distribution and conversion business.',mob,roles=['commercial_partner'],typ='product',sector='robotics',sub='autonomy_and_components'),
 p('Automotive Parts','Automotive parts supply and sales for vehicle production and aftermarket channels.',mob,roles=['commercial_partner'],typ='product',sector='robotics',sub='autonomy_and_components'),
 p('Refrigerated Vaccine Transport Vehicles','Refrigerated transport vehicles developed with Toyota Motor and B Medical Systems for vaccine cold-chain logistics.',mob,roles=['developer','commercial_partner'],typ='product',sector='robotics',sub='autonomy_and_components'),
 p('Embedded Automotive Software','Embedded software and connected-vehicle security and communications solutions.',dig,roles=['developer','commercial_partner'],typ='technology',sector='robotics',sub='robotics_software'),
 p('Electronic Devices and Semiconductors','Electronic devices and semiconductor products sold into automotive, home-appliance, communications and industrial equipment markets.',dig,roles=['commercial_partner'],typ='product',sector='semiconductors',sub='chip_design'),
 p('Mobility Materials','Steel sheets, bars, wire rods, pipes and specialty-steel products for mobility applications.',met,roles=['commercial_partner'],typ='product',sector='semiconductors',sub='chip_design'),
 p('Healthcare and Medical Products','Sales and rental of nursing-care and medical-related products through the healthcare and medical business.',life,roles=['commercial_partner'],typ='product',sector='biotech',sub='medical_devices'),
]
m={'batch_id':'batch-0445','companies':[{'company_id':cid,'products':products,'evidence':[ev(mob,'Official Toyota Tsusho Mobility Division page.'),ev(dig,'Official Toyota Tsusho Digital Solutions Division page.'),ev(met,'Official Toyota Tsusho Metal+ Division page.'),ev(life,'Official Toyota Tsusho Lifestyle Division page.')],'status':'partial','coverage_note':'Official business pages identify product families and commercial offerings; individual third-party brands and subsidiary SKUs were not attributed to Toyota Tsusho without explicit ownership evidence.'}]}
Path('/home/ec2-user/product-web-rebuild/batch-0445.json').write_text(json.dumps(m,indent=2))
