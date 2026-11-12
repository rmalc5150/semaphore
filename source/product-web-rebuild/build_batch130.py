from research_helpers import *
a=ev('https://www.fluxpower.com/lithium-ion-battery-resources','Current manufacturer resource catalogue directly reviewed, distinguishing G1 and G2 pack brochures. Capacities/configurations not invented by interpolating ranges.')
b=ev('https://www.fluxpower.com/hubfs/Flux%20Power%20Software%20Update%20%282%29.pdf','Official historical firmware support table explicitly identifies older pack models/capacities and partial item-number patterns; unknown suffixes NOT expanded into invented part numbers. Current availability of legacy configurations unverified.')
c=ev('https://www.fluxpower.com/hubfs/X-Series%20Battery%20Pack%20-%20Brochure.pdf','2022 manufacturer Xseries brochure confirms X36/48/80 capacities. Energy figures use inconsistent class-versus-nominal voltages, so not normalized into rated energies.')
d=ev('https://www.fluxpower.com/product/c-series','Current C48 product page states210Ah,51.2V nominal,10.7kWh;2024G2 brochure incorrectly lists5.0kWh for samecapacity/voltage. Current-page energy kept as manufacturer claim, conflicting PDF noted.')
e=ev('https://www.fluxpower.com/energy-management-solution','Current SkyEMS cloud platform page names SkyVox telematics hardware. Current Xseries/Cseries pages link legacy SkyBMS name to same energy-management page; software brand lineage grouped, not duplicate cloud product.')
f=ev('https://www.fluxpower.com/product/x-series','Current Xseries page links G2X48 and legacy SkyBMS to current energy-management URL. Actual battery cells not assumed manufactured by pack integrator.')
ps=[];es=[a,b,c,d,e,f]
base='https://www.fluxpower.com/hubfs/2024%20Product%20Brochures/'
files={'S8':'SA-800_Product%20Brochure%20G1-S8-Rev_B.pdf','S24':'SA-801_Product%20Brochure%20G1-S24-Rev_B.pdf','M24':'SA-802_Product%20Brochure%20G1-M24-Rev_B.pdf','M36':'SA-803_Product%20Brochure%20G1-M36-Rev_B.pdf','L48':'SA-804_Product%20Brochure%20G1-L48-Rev_B.pdf','X36':'SA-805_Product%20Brochure%20G1-X36-Rev_B.pdf','GSE3':'SA-808_Product%20Brochure%20G1-GSE3-Rev_B.pdf','M24-G2':'SA-809_Product%20Brochure%20G2-M24-Rev_B.pdf','M36-G2':'SA-810_Product%20Brochure%20G2-M36-Rev_B.pdf','L36-G2':'SA-811_Product%20Brochure%20G2-L36-Rev_B.pdf','X48-G2':'SA-812_Product%20Brochure%20G2-X48-Rev_B.pdf','C48-G2':'SA-814_Product%20Brochure%20G2-C48-Rev_B.pdf','G80-G2':'SA-813_Product%20Brochure%20G2-G80-Rev_B.pdf'}
def add(model,cap,life='commercial',config=None,source=None,**attrs):
 src=source or (ev(base+files[model],'Exact2024 manufacturer brochure model/capacity reviewed; generation retained. No per-capacity part number invented.') if model in files else b);es.append(src)
 attrs={'manufacturer_model':model,'capacity_ah':cap,'chemistry':'LiFePO4','identity_scope':'listed capacity configuration; not asserted distinct manufacturer part number',**attrs}
 if config:attrs['configuration']=config
 name='Flux Power '+model+' '+str(cap)+'Ah'+(' '+config if config else '')
 ps.append(p(name,'Lithium-iron-phosphate industrial battery pack capacity configuration.',src,life,roles=['manufacturer'],typ='product',sector='energy_storage',sub='batteries',attributes=attrs,evidence=[src,a]+([b] if life=='unknown' else [])))
for cap in [72,75,100,180]:add('S8',cap,'unknown',source=b)
add('S8',105,nominal_voltage_v=25.6)
add('S24',100,'unknown',source=b)
for cap in [105,210]:add('S24',cap,nominal_voltage_v=25.6)
for cap in [400,576]:add('M24',cap,'unknown',source=b)
add('M24',420,nominal_voltage_v=25.6)
add('M36',600,'unknown',source=b)
add('M36',630,nominal_voltage_v=38.4)
add('L48',420,nominal_voltage_v=51.2)
for cap in [600,800]:add('X36',cap,'unknown',source=b)
for cap in [630,840]:add('X36',cap,nominal_voltage_v=38.4)
add('X48',600,'unknown',source=b)
add('X48',630,'unknown',source=c,nominal_voltage_v=51.2)
add('X80',400,'unknown',source=b)
add('X80',420,'unknown',source=c,nominal_voltage_v=76.8)
add('GSE3',300,'unknown',source=b)
add('GSE3',315,nominal_voltage_v=76.8)
add('GSE',420,'unknown',source=b)
add('M24-G2',840,nominal_voltage_v=25.6,max_continuous_charge_current_a=300,energy_specification_note='Brochure states20.16kWh with840Ah and25.6V nominal; normalized energy withheld.')
add('M36-G2',840,nominal_voltage_v=38.4,manufacturer_stated_energy_kwh=32.3,max_continuous_charge_current_a=300)
for cap,energy in [(630,24.1),(840,32.3)]:add('L36-G2',cap,nominal_voltage_v=38.4,manufacturer_stated_energy_kwh=energy,max_continuous_charge_current_a=300)
for cap,energy in [(630,32.3),(840,43.0)]:add('X48-G2',cap,nominal_voltage_v=51.2,manufacturer_stated_energy_kwh=energy,max_continuous_charge_current_a=300)
add('C48-G2',210,source=d,nominal_voltage_v=51.2,manufacturer_stated_energy_kwh=10.7,energy_specification_note='Current product-page10.7kWh;2024brochure5.0kWh conflicts, not imported as alternative model.',application='AGV/AMR/industrial equipment')
for config,cap,energy,current in [('1P',210,16.1,125),('2P',420,32.3,250),('4P',840,64.5,500)]:add('G80-G2',cap,config=config,nominal_voltage_v=76.8,manufacturer_stated_energy_kwh=energy,max_continuous_charge_current_a=current)
ps.append(p('SkyEMS','Cloud energy-management and fleet battery telemetry software; manufacturer-linked legacy SkyBMS cloud name grouped under current offering.',e,'commercial',aliases=['SkyBMS'],typ='technology',sector='energy_storage',sub='batteries',evidence=[e,f],attributes={'brand_mapping_basis':'manufacturer SkyBMS links resolve to current SkyEMS energy-management page; exact hardware/embedded-BMS version mapping unverified'}))
ps.append(p('SkyVox','Named battery telematics data-transmission hardware supporting SkyEMS cloud monitoring.',e,'commercial',typ='product',sector='energy_storage',sub='batteries'))
cs=[company('Flux Power Holdings Inc',ps,es,'37 reviewed identities/configurations:25 G1/historical capacity configurations,10G2 capacity configurations andSkyEMS/SkyVox. Legacy firmware capacities unknown current availability;2024 manufacturer-listed packs retain generation/capacity, incomplete item-number patterns not expanded. C48current-page10.7kWh distinguished from PDF5.0kWh error;M24G2energy withheld. Full current mechanical/OEM variants, internal part suffixes, older BMS hardware/charger products and exact SkyBMS version lineage still require verification.')]
(out/'batch-0130.json').write_text(json.dumps({'companies':cs},indent=2));print(len(ps))
