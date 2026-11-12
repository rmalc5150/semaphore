from research_helpers import *
base='https://www.tractorsupply.com/tsc/product/'
products=[];evidence=[]
def add(name,path,desc,sector='energy_storage',attrs={},life='commercial'):
 e=ev(base+path,'Direct retailer catalogue identifies product offered by Tractor Supply. Retail commercial-partner relationship only; brand manufacturer ownership not inferred. Location-specific stock not treated as worldwide availability.')
 e['source']='official_retailer_product_page';evidence.append(e)
 products.append(p(name,desc,e,life,typ='product',sector=sector,sub='batteries' if sector=='energy_storage' else 'service_robotics',roles=['commercial_partner'],territory='United States',attributes=attrs))
for code,item,path,desc in [
 ('TS/IB-U1L350','2086805','traveller-12v-415a-rider-mower-battery-u1l-355-2086805','12 V rider-mower battery, 350 cold-cranking amps.'),
 ('TS/IB-U1L300','2086806','traveller-12v-350a-rider-mower-battery-u1l-300-2086806','12 V rider-mower battery, 300 cold-cranking amps.'),
 ('TS/IB-U1L250','2086807','traveller-12v-250a-rider-mower-battery-u1l-250-2086807','12 V rider-mower battery, 250 cold-cranking amps; left-terminal variant.'),
 ('TS/IB-U1R250','2086808','traveller-12v-300cca-rider-mower-battery-u1r-250-2086808','12 V rider-mower battery, 250 cold-cranking amps; right-terminal variant.'),
 ('TS/IB-12S','2472156','traveller-12v-210-cca-replacement-lawn-and-garden-battery-with-agm-technology-2472156','12 V AGM lawn-and-garden battery, 210 cold-cranking amps.'),
 ('TS/IB-U1L215','2086809','traveller-12v-260a-rider-mower-battery-u1l-215-2086809','12 V rider-mower battery, 215 cold-cranking amps.')]:
 add('Traveller '+code,path,desc,attrs={'manufacturer_part_number':code,'retailer_item_number':item,'voltage_v':12})
add('Universal Battery D5741','universal-battery-12v-5ah-sealed-lead-acid-(sla)-agm-battery-with-f1-terminals-2273558','Sealed lead-acid AGM battery with F1 terminals.',attrs={'manufacturer_part_number':'D5741','retailer_item_number':'2273558','voltage_v':12,'capacity_ah':5})
add('Greenworks 29462 battery','greenworks-g-max-40v-2ah-li-ion-battery-1131622','G-MAX lithium-ion tool battery.',attrs={'manufacturer_part_number':'29462','retailer_item_number':'1131622','voltage_v':40,'capacity_ah':2})
add('Yard Force Revola X4E','yard-force-revola-x4e-robot-mower','Autonomous lawn mower with charging station and boundary kit. Conflicting battery capacities in listing withheld.','robotics',attrs={'model':'RVX4E','retailer_item_number':'2536530','conflicting_specifications':'battery capacity 2.9Ah versus4.0Ah; unnormalized'})
add('Yard Force NX100i','yard-force-nx100i-robot-mower','Autonomous lawn mower with automatic docking and boundary kit.','robotics',attrs={'retailer_item_number':'2536531','battery_voltage_v':28,'battery_capacity_ah':2.9})
for model,wh,path in [
 ('100594',1638,'champion-power-equipment-1638-wh-3200-1600-watt-lithium-ion-solar-generator-portable-power-station-backup-battery-100594'),
 ('100593',3276,'champion-power-equipment-3276-wh-3200-1600-watt-lithium-ion-solar-generator-portable-power-station-backup-battery-100593'),
 ('201260',998,'champion-power-equipment-998-wh-2000-1000-watt-lithium-ion-solar-generator-portable-power-station-backup-battery-2325866'),
 ('201189',579,'champion-power-equipment-579-wh-1200w-600-watt-lithium-ion-solar-generator-portable-power-station-backup-battery-201189-2325865'),
 ('285Wh portable power station',285,'champion-power-equipment-285-wh-600-300-watt-lithium-ion-solar-generator-portable-power-station-backup-battery')]:
 add('Champion Power Equipment '+model,path,'Portable lithium-ion battery power station; solar-rechargeable storage system, distinct from generation-only solar panels.',attrs={'capacity_wh':wh,'ordering_model':model if model.isdigit() else 'unverified'})
add('Yard Force PB-2400','yard-force-2400w-pure-sine-2536537','Portable battery power station with pure-sine AC output.',attrs={'manufacturer_model':'PB-2400','capacity_wh':1920,'continuous_output_w':2400})
add('Cummins 592Wh portable power station','cummins-600-watt-solar-powered-portable-power-station-592wh-lithium-ion-battery-1-200w-solar-generator-pure-sine-wave-2590300','Retail-listed lithium-ion battery power station. Brand licensing/manufacturer relationship not inferred.',attrs={'retailer_item_number':'2590300','capacity_wh':592,'continuous_output_w':600})
co=company('Tractor Supply Company',products,evidence,'Initial retail catalogue review: eight separately coded batteries, two robot mowers and seven portable battery power stations. Retail partnership only; no direct manufacturing claim. Differing left/right terminal variants kept separate. Conflicting Revola battery capacity withheld. Need remaining37-item mower battery catalogue, automotive/marine/deep-cycle/powersport/tool/household batteries, power banks, further robot models and other storage categories, exact manufacturer codes/stock status, and cross-company shared product identity review. Not a full catalogue scan; partial.')
(out/'batch-0169.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
