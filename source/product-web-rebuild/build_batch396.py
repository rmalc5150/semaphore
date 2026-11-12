from research_helpers import *
a=ev('https://ambiq.com/products/','Current named semiconductor catalogue; upcoming Atomiq kept in development. Product families not expanded into unverified ordering variants.')
b=ev('https://ambiq.com/product/apollo510-lite-series/','Three named Lite SoCs and evaluation board; ordering variants reviewed. Bluetooth connectivity differs by model.')
c=ev('https://ambiq.com/product/apollo330-plus-series/','Three named Plus variants and evaluation board. Matter/Thread OTA functionality described as future; unrelated Apollo3 Blue Plus comparison row not used as Apollo330 specification.')
d=ev('https://ambiq.com/product/apollo510b/','Current Bluetooth-enabled Cortex-M55 SoC, ordering information and evaluation board confirmed.')
products=[]
for n in ['Apollo510','Apollo4 Blue Plus','Apollo4 Blue Lite','Apollo4 Blue','Apollo4 Plus','Apollo4 Lite','Apollo4','Apollo3 Blue Plus','Apollo3 Blue','Apollo3 Blue Thin','Apollo3','Apollo2 Thin','Apollo2','Apollo']:
 products.append(p('Ambiq '+n,'Ultra-low-power '+n+' microcontroller/system-on-chip offering listed in the current Ambiq catalogue; exact ordering variants remain to be enumerated.',a,life='commercial',typ='product',sector='semiconductors',sub='chip_design'))
for n,desc in [('Apollo510 Lite','Cortex-M55 edge-processing SoC; base variant without integrated radio in the reviewed comparison.'),('Apollo510B Lite','Cortex-M55 SoC with Bluetooth Low Energy 5.4.'),('Apollo510D Lite','Cortex-M55 SoC with Bluetooth Low Energy 5.4 and Bluetooth Classic.')]:
 products.append(p('Ambiq '+n,desc,b,life='commercial',typ='product',sector='semiconductors',sub='chip_design'))
for n,desc in [('Apollo330 Plus','Low-power Cortex-M55 edge-AI SoC; base variant.'),('Apollo330B Plus','Cortex-M55 edge-AI SoC with Bluetooth Low Energy 5.4.'),('Apollo330M Plus','Cortex-M55 edge-AI SoC with dual-mode Bluetooth; Matter and Thread support described as a future OTA update.')]:
 products.append(p('Ambiq '+n,desc,c,life='commercial',typ='product',sector='semiconductors',sub='chip_design'))
products.append(p('Ambiq Apollo510B','Cortex-M55 edge-AI SoC with Bluetooth Low Energy 5.4 and dedicated network coprocessor.',d,life='commercial',typ='product',sector='semiconductors',sub='chip_design'))
for n in ['AM1815','AM1805','AM0815','AM0805']:
 products.append(p('Artasie '+n,'Ultra-low-power real-time-clock integrated circuit.',a,life='commercial',typ='product',sector='semiconductors',sub='chip_design'))
products.append(p('Ambiq Atomiq','Upcoming ultra-low-power system-on-chip line; commercial availability not established.',a,life='development',typ='development_program',sector='semiconductors',sub='chip_design'))
for n,src,code in [('Apollo510 Lite Series Evaluation Board',b,'AP510DLEVB'),('Apollo330 Plus Series Evaluation Board',c,'AP330MPEVB'),('Apollo510B Evaluation Board',d,'AP510BEVB')]:
 products.append(p('Ambiq '+n,'Hardware evaluation board for the associated Ambiq SoC; development accessory, not a separate chip design.',src,life='commercial',typ='product',sector='semiconductors',sub='chip_design',attributes={'catalogue_category':'development_board','ordering_code':code}))
co=dict(company_id='cmp_329a71f3-3ca6-4eb1-9306-3e21ea40aaa6',products=products,evidence=[a,b,c,d],status='partial',coverage_note='29 named semiconductor offerings including 21 Apollo variants/families, four RTCs, upcoming Atomiq, and three evaluation boards. No parent series duplicate for the six separately enumerated Lite/330 variants. Partial: older chip ordering variants, other boards and accessories, AI runtimes/SDKs and named technology platforms require additional review. Atomiq is development; future Matter/Thread OTA functionality not represented as available.')
assert len(products)==29
(out/'batch-0396.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
