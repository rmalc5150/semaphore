import json
from pathlib import Path
from research_helpers import ev,p
cid='cmp_230480da-8e27-4292-af6b-f270b5916d74'; src='https://swiftech.com/'; kits='https://swiftech.com/kits.aspx'; pumps='https://swiftech.com/pumps.aspx'; blocks='https://swiftech.com/apogee.aspx'
products=[
 p('Apogee CPU Waterblocks','Swiftech Apogee family of CPU waterblocks for liquid-cooled PCs.',blocks,life='commercial',roles=['developer','owner'],typ='product',sector='robotics',sub='autonomy_and_components',aliases=['Apogee SKF','Apogee SKF LT','Apogee SKF Prestige','Apogee Drive II','Apogee LP']),
 p('Hydrae GT Series','Liquid-cooling radiators available in 120, 240 and 360 mm sizes.',src,life='commercial',roles=['developer','owner'],typ='product',sector='robotics',sub='autonomy_and_components'),
 p('HeliX 120 IRIS','120x25 mm fan with PWM speed control and addressable RGB lighting.',src,life='commercial',roles=['developer','owner'],typ='product',sector='robotics',sub='autonomy_and_components'),
 p('IRIS MB Link','Motherboard adapter for controlling addressable RGB lighting on Swiftech IRIS products.',src,life='commercial',roles=['developer','owner'],typ='product',sector='robotics',sub='autonomy_and_components'),
 p('Maelstrom D5 V2 Series','Pump and reservoir combination with addressable RGB lighting.',src,life='commercial',roles=['developer','owner'],typ='product',sector='robotics',sub='autonomy_and_components'),
 p('Boreas Series DIY Liquid Cooling Kits','DIY liquid-cooling kits including radiator, pump, reservoir, coolant and filling accessories.',kits,life='commercial',roles=['developer','owner'],typ='product',sector='robotics',sub='autonomy_and_components'),
 p('Drive X3 AIO','All-in-one CPU cooler with integrated pump and expandable standard G1/4 ports.',kits,life='commercial',roles=['developer','owner'],typ='product',sector='robotics',sub='autonomy_and_components'),
 p('MCP Pump Series','12 VDC centrifugal pumps and pump tops for custom liquid-cooling loops.',pumps,life='commercial',roles=['developer','owner'],typ='product',sector='robotics',sub='autonomy_and_components',aliases=['MCP655','MCP65X','MCP50X','MCP35X2']),
]
m={'batch_id':'batch-0442','companies':[{'company_id':cid,'products':products,'evidence':[ev(src,'Official Swiftech storefront product listing.'),ev(kits,'Official Swiftech liquid-cooling kits catalogue.'),ev(pumps,'Official Swiftech pumps catalogue.'),ev(blocks,'Official Swiftech Apogee CPU waterblocks catalogue.')],'status':'partial','coverage_note':'Official Swiftech catalogue pages identify the principal current product families; individual SKUs remain represented by family records and aliases.'}]}
Path('/home/ec2-user/product-web-rebuild/batch-0442.json').write_text(json.dumps(m,indent=2))
