from research_helpers import *
a=ev('https://www.m-chemical.co.jp/en/products/departments/mcc/anode/product/1201073_7544.html','Current manufacturer distinguishes MPG natural graphite and ICG artificial graphite anode material families; no exact grade codes provided.')
b=ev('https://www.m-chemical.co.jp/en/products/departments/group/muis/product/1211431_9448.html','Current group catalogue offers Sol-Rite electrolyte via MU Ionic Solutions; partnership not exclusive parent ownership inferred.')
c=ev('https://www.m-chemical.co.jp/en/products/field/electro/battery/index.html','Current battery material index identifies ethylene carbonate solvent. Repeated regular/high-purity title entries not assumed separate SKU without grade proof.')
d=ev('https://www.m-chemical.co.jp/en/products/field/electro/semiconmat/index.html','Current semiconductor material index identifies named families; service/FEOL/BEOL overview pages not separate product entries.')
e=ev('https://www.m-chemical.co.jp/en/products/departments/mcc/nes/product/1201029_9004.html','Current GaN page distinguishes offered HVPE wafer and developing SCAAT/SCAAT-LP growth processes; technology not duplicate wafer SKU.')
f=ev('https://www.m-chemical.co.jp/en/products/departments/mcc/semicon/product/1201033_8042.html','Star Series current lineup explicitly names hydrochloric acid; no other chemical species invented.')
g=ev('https://www.m-chemical.co.jp/en/products/departments/mcc/an/product/1201154_7720.html','Current product page confirms acrylamide-production biocatalyst commercial offering.')
h=ev('https://www.m-chemical.co.jp/en/csr/pdf/csr_report_mrc_2014.pdf','Historical issuer describes NBAT biocatalytic acrylamide process licensing. Current licence availability unverified.')
i=ev('https://www.m-chemical.co.jp/en/products/application/health/index.html','Current catalogue confirms MCI GEL chromatography packings for peptide/protein purification; research/bioprocess tool family, not medicine.')
j=ev('https://www.mcgc.com/english/ir/pdf/02625/02883.pdf','May2026 parent results confirm Tanabe pharmaceutical business transfer completedJuly1 2025. No automatic current attribution of Tanabe drugs to Mitsubishi Chemical Group.')
products=[]
for name,desc,source in [('MPG anode materials','Natural-graphite lithium-ion battery anode family.',a),('ICG anode materials','Artificial-graphite lithium-ion battery anode family.',a),('Sol-Rite electrolyte','Formulated battery electrolyte offered by group catalogue via MU Ionic Solutions.',b),('battery-grade ethylene carbonate','Electrolyte solvent; exact high-purity grade differentiation unresolved.',c)]:
 products.append(p('Mitsubishi Chemical '+name,desc,source,'commercial',typ='product',sector='energy_storage',sub='batteries',roles=['commercial_partner']))
for name,desc,source,typ,life in [
 ('M-Filleris NTE series','Negative thermal expansion filler family for semiconductor packaging.',d,'product','commercial'),
 ('HVPE GaN wafer','Single-crystal gallium nitride wafer family; individual wafer configurations unexpanded.',e,'product','commercial'),
 ('SCAAT','Acidic ammonothermal GaN crystal-growth technology.','e','technology','development'),
 ('SCAAT-LP','Low-pressure acidic ammonothermal GaN growth technology; distinct named process.',e,'technology','development'),
 ('synthetic silica powder','Ultrahigh-purity silica material for semiconductor quartz applications.',d,'product','commercial'),
 ('Lithomax','Photosensitive polymer family used in semiconductor photoresists.',d,'product','commercial'),
 ('aquaSAVE','Antistatic coating for electron-beam lithography.',d,'product','commercial'),
 ('aquaPASS','Polyaniline-based antistatic material offered in semiconductor materials catalogue.',d,'product','commercial'),
 ('MCX-SDR4','Post-CMP cleaning material for copper/low-k semiconductor processing.',d,'product','commercial'),
 ('MC1 RCA cleaning solution','Semiconductor cleaning chemical family for RCA process.',d,'product','commercial'),
 ('Star Series hydrochloric acid','Ultrapure hydrochloric acid for semiconductor wafer cleaning.',f,'product','commercial')]:
 if source=='e':source=e
 products.append(p('Mitsubishi Chemical '+name,desc,source,life,typ=typ,sector='semiconductors',sub='materials_and_packaging',roles=['commercial_partner']))
products.extend([
 p('Mitsubishi Chemical acrylamide biocatalyst','Microbial enzyme catalyst used for industrial acrylamide synthesis.',g,'commercial',typ='product',sub='industrial_biotechnology',roles=['commercial_partner']),
 p('Mitsubishi NBAT acrylamide process','Historical licensed biocatalytic production technology; current licence status unverified.',h,typ='technology',sub='industrial_biotechnology',roles=['commercial_partner']),
 p('Mitsubishi MCI GEL chromatography packings','Polymer chromatography media for biological molecule purification; exact resin grades pending.',i,'commercial',typ='product',sub='research_tools',roles=['commercial_partner'])])
co=company('Mitsubishi Chemical Holdings Corporation',products,[a,b,c,d,e,f,g,h,i,j],'Initial18 battery material, semiconductor material/process and bioprocess offerings reviewed. MPG/ICG distinct; repeated ethylene carbonate listings grouped until grade identity proved. Current Tanabe transferJuly1 2025 verified; former drug catalogue requires dated relationships. Need fullGelest/DIAION/MCIgrade catalogue,packaging resins andfilm variants,ALSET/SUPERIO explicitstorage configuration,wafer grades/chemicals,biobased polymer production evidence,currentbiocatalyst licences and historicalpharma products. Genericoverview/servicepages notproducts. Parentcommercial_partner only. Partial.')
(out/'batch-0177.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
