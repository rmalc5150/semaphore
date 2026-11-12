from research_helpers import *
rows=[
('GFMD-C','https://www.sacredsun.com/Product/LeadAcid/Energy/2025/1124/gfmd-power-utility-battery.html','AGM battery.', 'GFMD-100C GFMD-150C GFMD-200C GFMD-300C GFMD-400C GFMD-500C GFMD-600C GFMD-800C GFMD-1000C GFMD-1200C GFMD-1500C GFMD-2000C GFMD-2500C GFMD-3000C'.split()),
('GFM-H','https://www.sacredsun.com/Product/LeadAcid/Telecom/2020/1120/gfmh-high-floating-battery.html','AGM battery.','GFM-500H GFM-600H GFM-800H GFM-1000H GFM-1500H GFM-2000H'.split()),
('GFM-C','https://sacredsun.com/Product/LeadAcid/Telecom/2020/1120/gfmc-standby-battery.html','AGM battery.','GFM-100CL GFM-150CL GFM-200C GFM-300C GFM-400C GFM-400CL GFM-500C GFM-600C GFM-800C GFM-1000C 6GFM-38 6GFM-50 6GFM-65 6GFM-80 6GFM-100 6GFM-150 6GFM-200'.split()),
('GFMJ','https://www.sacredsun.com/Product/LeadAcid/Energy/2020/1120/gfmj-gel-battery.html','Gel lead-acid battery.','GFMJ-200 GFMJ-300 GFMJ-400 GFMJ-500 GFMJ-600 GFMJ-800 GFMJ-1000'.split()),
('SAJ','https://www.sacredsun.com/Product/LeadAcid/Energy/2020/1120/saj-agm-gel-battery.html','AGM/gel battery.','SAJ12-38 SAJ12-65 SAJ12-80 SAJ12-100 SAJ12-150 SAJ12-200'.split()),
('SDC','https://www.sacredsun.com/Product/LeadAcid/Energy/2020/1120/sdc-motive-battery.html','Deep-cycle AGM/gel battery.','SDC12-75 SDC12-90 SDC12-110 SDC12-130 SDC12-170 SDC12-200 SDC6-195 SDC6-235 SDC6-290'.split()),
('GFMG','https://www.sacredsun.com/Product/LeadAcid/Standby/2020/1120/gfmg-high-power-battery.html','High-power AGM battery.','GFMG-200 GFMG-275 GFMG-300 GFMG-320 GFMG-400 GFMG-515 3GFMG-105 3GFMG-125 3GFMG-200'.split()),
('OPzV','https://www.sacredsun.com/Product/LeadAcid/Telecom/2020/1120/OPzV-gel-long-life-battery.html','Tubular gel battery.','4OPzV200 5OPzV250 6OPzV300 5OPzV350 5OPzV350A 6OPzV420 6OPzV420A 7OPzV490 7OPzV490A 7OPzV500 6OPzV600 8OPzV800 10OPzV1000 10OPzV1000A 12OPzV1200 15OPzV1500 15OPzV1500A 16OPzV2000 16OPzV2000A 20OPzV2500 20OPzV2500A 24OPzV3000 24OPzV3000A'.split()+['12V 1 OPzV 50','12V 2 OPzV 100','12V 3 OPzV 150']),
('DCS','https://www.sacredsun.com/Product/LeadAcid/Energy/2020/1120/dcs-deep-cycle-battery.html','Deep-cycle storage battery.','DCS12-50 DCS12-100 DCS12-200'.split()),
('FMJ','https://www.sacredsun.com/Product/LeadAcid/Energy/2020/1204/FMJ-gel-battery.html','Gel lead-acid battery.','6FMJ-33 6FMJ-50 6FMJ-65 6FMJ-85 6FMJ-100 6FMJ-120 6FMJ-150 6FMJ-200'.split()),
('FT','https://www.sacredsun.com/Product/LeadAcid/Telecom/2020/1204/ft-front-terminal-battery.html','Front-terminal AGM battery.','FTB12-80 FTB12-95 FTB12-100 FTB12-105 FTB12-125 FTB12-150 FTA12-100 FTA12-125 FTA12-150 FTA12-170 FTA12-180 FTA12-190 FTA12-200'.split())]
products=[];evidence=[]
for family,url,desc,names in rows:
 e=ev(url,'Official product table lists individual '+family+' battery models; series retained as an attribute, not an extra duplicate product.')
 evidence.append(e)
 for name in names:products.append(p(name,desc,e,'commercial',['manufacturer'],typ='product',sector='energy_storage',sub='batteries',attributes={'product_family':family}))
L=ev('https://sacredsun.com/Product/Battery/2024/0122/High-Voltage-Li-ion-Battery.html','Official ESS page explicitly identifies SHSIFP76100A LFP module.')
H=ev('https://www.sacredsun.com/Product/Battery/2024/0122/Residential-HV-Enerstack-Battery.html','Named HV Enerstack residential battery system.')
LV=ev('https://www.sacredsun.com/News/News/2022/0927/FNS-Power-Launch-At-REplus2022-SPI2022.html','Issuer names LV EnerStack battery system; historical availability not presumed current.')
E=ev('https://www.sacredsun.com/Product/Power/2020/1216/Renewable-ESS.html','Issuer names Gripline G6-10-US and ESS-20H-1229kWh / ESS-40H-2765kWh; subsidiary FNS identified as manufacturer.')
EU=ev('https://sacredsun.com/Product/Power/2020/1216/Renewable-ESS.html','Issuer names Gripline G5-10 for EU/Australia; distinct from US G6-10 variant.')
F=ev('https://www.sacredsun.com/News/News/2020/1117/cooperation-Furukawa-Battery.html','Issuer states Furukawa developed FCP and authorized Sacred Sun manufacture; no Sacred Sun original-development role inferred.')
for n,d,e,life in [('SHSIFP76100A','LFP energy storage battery module.',L,'commercial'),('HV Enerstack Battery','High-voltage residential battery system.',H,'commercial'),('LV EnerStack Battery','Historical low-voltage residential battery system.',LV,'unknown'),('Gripline G6-10-US','US residential battery/inverter system.',E,'commercial'),('Gripline G5-10','EU/Australia residential battery/inverter system.',EU,'commercial'),('ESS-20H-1229kWh','Containerized energy storage system.',E,'commercial'),('ESS-40H-2765kWh','Containerized energy storage system.',E,'commercial')]:products.append(p(n,d,e,life,['manufacturer'],typ='product',sector='energy_storage',sub='batteries'))
for model,url in [('FCP-500','https://www.sacredsun.com/uploads/pdf/FCP/FCP-500.pdf'),('FCP-1000','https://www.sacredsun.com/uploads/pdf/FCP/FCP-1000.pdf')]:
 fe=ev(url,'Official named lead-carbon cell datasheet; historical commercial model, current availability unresolved.')
 evidence.append(fe);products.append(p(model,'Historical lead-carbon storage cell.',fe,roles=['manufacturer','licensee'],typ='product',sector='energy_storage',sub='batteries',evidence=[fe,F],attributes={'product_family':'FCP'}))
evidence += [L,H,LV,E,EU,F]
companies=[company('Shandong Sacred Sun Power Sources Co Ltd',products,evidence,'Eleven official lead-acid/gel model tables and selected lithium/ESS systems plus licensed FCP cells reviewed. Remaining lithium, high-rate/telecom and traction models, FCP modules and historical system names require further reconciliation. Generic energy projects are not product rows.')]
(out/'batch-0010.json').write_text(json.dumps({'companies':companies},indent=2))
print(len(products))
