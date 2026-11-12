from research_helpers import *
A=ev('https://www.gvs.com/en/catalog/liquid-media-ampoules','Current catalogue21 exact ampoule codes, all2mL; MFCrosolic acid codes10496114/195 have different listed sterilization cycles. No inferred clinical diagnostic approval.')
B=ev('https://www.gvs.com/en/catalog/bottled-media','Current four exact bottled-media items: TSBsingle/double strength100mL, MIagar/broth50mL.')
M=ev('https://www.gvs.com/en/catalog/manifolds-and-accessories','Current manufacturer exact catalogue manifold model and kit codes; branch counts and included filter cups reviewed.')
F=ev('https://www.gvs.com/en/catalog/analytical-funnels','Current nitrocellulose microbiology monitors differentiated by diameter/pore/grid; separately bagged10497501 grouped with10497500 as packaging variant.')
ps=[]
for x in json.loads((out/'gvs-reviewed-ampoules.json').read_text()):
 attrs={'manufacturer_part_number':x['code'],'medium':x['name'].removeprefix('Ampoules '),'volume_ml':2,'research_use':'microbiological culture/enumeration; not a medicine'}
 if x['code'] in ['10496114','10496195']:attrs['catalogue_sterilization_cycle']='2min104C' if x['code']=='10496114' else '2min115C'
 ps.append(p('GVS '+x['code'],'Ready-to-use microbiological culture-medium ampoule.',A,'commercial',roles=['manufacturer'],typ='product',sub='research_tools',attributes=attrs))
for code,medium,volume in [('10496707','TSB single strength',100),('10496708','TSB double strength',100),('10496847','MI agar',50),('10496851','MI broth',50)]:
 ps.append(p('GVS '+code,'Bottled microbiological culture medium.',B,'commercial',roles=['manufacturer'],typ='product',sub='research_tools',attributes={'manufacturer_part_number':code,'medium':medium,'volume_ml':volume}))
for code,n,volume in [('MANIFW16700323A',3,None),('MANIFW16700326A',6,None),('MANIFW16710123A',3,300),('MANIFW16710124A',3,500),('MANIFW16710126A',6,300),('MANIFW16710127A',6,500),('MANIFW16710323A',3,None),('MANIFW16710324A',3,100),('MANIFW16710326A',6,None),('MANIFW16710327A',6,100),('MANIFW16711023A',3,None),('MANIFW16711026A',6,None),('MANIFW16711088A',3,None),('MANIFW16711089A',6,None)]:
 attrs={'manufacturer_part_number':code,'branches':n,'material':'stainless steel'}
 if volume:attrs.update(included_cups=n,cup_capacity_ml=volume)
 if code in ['MANIFW16711023A','MANIFW16711026A']:attrs['connection']='Gravi-Seal or rubber-stopper devices'
 ps.append(p('GVS '+code,'Microbiological sample-filtration manifold'+(' with filter cups.' if volume else '.'),M,'commercial',roles=['manufacturer'],typ='product',sub='research_tools',attributes=attrs))
for code,diam,pore,grid in [('10497511',47,.2,'white/black'),('10497603',56,.2,'white/black'),('10497500',47,.45,'white/black'),('10497600',56,.45,'white/black'),('10497502',47,.45,'black/white'),('10497601',56,.45,'black/white'),('10497503',47,.8,'black/white'),('10497602',56,.8,'black/white')]:
 attrs={'manufacturer_part_number':code,'membrane_material':'nitrocellulose','diameter_mm':diam,'pore_size_micrometres':pore,'grid_colours':grid}
 if code=='10497500':attrs['individual_bag_packaging_variant_code']='10497501'
 ps.append(p('GVS '+code,'Sterile filtration-and-culture microbiological monitor.',F,'commercial',roles=['manufacturer'],typ='product',sub='research_tools',attributes=attrs))
cs=[company('GVS S.p.A.',ps,[A,B,M,F],'Forty-seven current exact microbiology products reviewed. Packaging-only monitor10497501 grouped with10497500. Full membranes, filtration/syringe equipment, protein analysis, bioprocessing, blood treatment and semiconductor/battery-specific filters remain to research; accessories/pack-size duplicates not blindly expanded.')]
(out/'batch-0100.json').write_text(json.dumps({'companies':cs},indent=2));print(len(ps))
