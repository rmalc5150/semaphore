from research_helpers import *
base='https://www.fujielectric.com/products/semiconductors_devices/semiconductor/product_series/'
a=ev(base+'model_power_supply_ac_dc_ic_general_pwm.html','Exact general PWM ICs reviewed in current official product table.')
b=ev(base+'model_power_supply_ac_dc_ic_pseudo_resonance.html','Public HTML table downloaded and manually reviewed after browser timeout; ten exact quasi-resonant controller models.')
c=ev(base+'model_power_supply_high_side_low_side.html','Current single-model high/low-side driver table.')
d=ev(base+'model_pressure.html','Current integrated semiconductor pressure-sensor table; exact model EPL4PC-R3S.')
products=[]
for names,src,desc in [('FA13842N FA13843N FA13844N FA13845N FA5504N FA5510N FA5511N FA5515N FA3641N FA3647N FA5604N FA5605N FA5606N FA5607N',a,'PWM controller IC.'),('FA5640N FA5641N FA5642N FA5643N FA5644N FA5648N FA5570N FA5571N FA5573N FA5577N',b,'Quasi-resonant controller IC.'),('FA5650N',c,'High-side/low-side driver IC.'),('EPL4PC-R3S',d,'Integrated semiconductor pressure sensor.')]:
 for name in names.split():products.append(p(name,desc,src,life='commercial',typ='product',sector='semiconductors',sub='chip_design',roles=['developer','manufacturer']))
co=dict(company_id='cmp_2c33c39d-0af2-4555-b8d2-808c6be581db',products=products,evidence=[a,b,c,d],status='partial',coverage_note='Eighty-seven exact IC/sensor models across six power-controller tables and the integrated pressure-sensor table. Partial: IGBT and SiC modules/discretes, automotive devices, historical controller grades and qualifying storage systems remain. No speculative suffix variants or broad generic module categories counted as individual models.')
(out/'batch-0353.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
