from research_helpers import *
a=ev('https://www.iqep.com/products/gaas','Named GaAs device-structure epiwafer offerings; device families not asserted packaged IQE chips.')
b=ev('https://www.iqep.com/products/inp','Named InP epiwafer structure families.')
c=ev('https://www.iqep.com/products/gan','RF GaN offerings commercial; power and microLED roadmap products not assumed commercially released.')
d=ev('https://www.iqep.com/products/gasb/','Named antimonide infrared epiwafer families.')
e=ev('https://www.iqep.com/products/substrates','Five named semiconductor substrate material families; custom doping/size variants not invented.')
f=ev('https://www.iqep.com/media/press-releases/2026/iqe-announces-purchase-agreement-with-quintessent-as-quantum-dot-laser-technology-moves-to-customer-sampling/','September 2026 QDL epitaxy supply supporting customer sampling; not finished Quintessent laser product ownership.')
products=[]
def add(names,src,desc,life='commercial'):
 for n in names:products.append(p('IQE '+n,desc,src,life,roles=['manufacturer'],sector='semiconductors',sub='materials_and_packaging',typ='product'))
add(['GaAs pHEMT epiwafers','GaAs MESFET epiwafers','GaAs HFET epiwafers','GaAs PIN diode epiwafers','GaAs Schottky diode epiwafers','InGaP/GaAs HBT epiwafers','InGaP/GaAs BiFET epiwafers','InGaP/GaAs BiHEMT epiwafers','AlGaAs/GaAs HBT epiwafers','AlGaAs/GaAs BiFET epiwafers','AlGaAs/GaAs BiHEMT epiwafers','850 nm VCSEL epiwafers','940 nm VCSEL epiwafers','1060 nm VCSEL epiwafers','QWIP epiwafers','AlGaInP/GaAs red laser-diode epiwafers','AlGaInP/GaAs red LED epiwafers','GaAs-on-Ge integration platform'],a,'Epitaxial semiconductor structure family.')
add(['InP FP laser epiwafers','InP DFB laser epiwafers','InP EML epiwafers','InP quantum cascade laser epiwafers','InP APD epiwafers','InP photodiode epiwafers','InP SWIR detector epiwafers','InP extended-wavelength detector epiwafers','InP HBT epiwafers','InP HEMT epiwafers'],b,'Epitaxial semiconductor structure family.')
add(['GaN RF HEMT-on-SiC epiwafers','GaN RF HEMT-on-Si epiwafers'],c,'RF epitaxial structure family.')
add(['650 V D-mode GaN HEMT epiwafers','650 V E-mode GaN HEMT epiwafers','Vertical GaN-on-GaN epiwafers','GaN-on-Sapphire power epiwafers','Blue GaN-on-Si microLED epiwafers','Green GaN-on-Si microLED epiwafers','Red GaN-on-Si microLED epiwafers'],c,'Named power/display structure; commercial release unconfirmed.','unknown')
add(['GaSb T2SL detector epiwafers','GaSb nBn detector epiwafers','GaSb interband-cascade detector epiwafers','GaSb MWIR laser epiwafers','GaSb LWIR laser epiwafers'],d,'Infrared epitaxial structure family.')
add(['GaAs substrates','GaSb substrates','InP substrates','InSb substrates','InAs substrates'],e,'Semiconductor substrate material family.')
add(['Quantum Dot Laser epitaxy'],f,'Foundry-ready GaAs epitaxy supplied for customer sampling.','development')
co=dict(company_id='cmp_29c8da87-2163-47ac-a8b1-e3de13c544d3',products=products,evidence=[a,b,c,d,e,f],status='partial',coverage_note='Forty-eight published material/device-structure families. Partial: diameter, orientation, doping and custom layer-stack variants and legacy branded integration processes remain. Finished customer semiconductor devices not attributed as IQE designs. GaN power/display release unconfirmed despite named roadmap offerings. Device-structure/wavelength alternatives explicitly published, not invented orderable part numbers.')
(out/'batch-0312.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
