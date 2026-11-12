from research_helpers import *
base='https://www.fujielectric.com/products/semiconductors_devices/semiconductor/product_series/'
a=ev(base+'model_power_supply_ac_dc_ic_low_pwm.html','Current official product table; exact green-mode PWM IC part numbers manually reviewed.')
b=ev(base+'model_power_supply_ac_dc_ic_power_factor.html','Current official tables; critical and continuous conduction PFC IC models reviewed.')
c=ev(base+'model_power_supply_ac_dc_ic_current_resonance.html','Current official LLC controller table; FA6C65N brochure title differs from actual FA6C64N product table, so only table identities recorded.')
products=[]
for names,src,desc in [('FA8C71N FA8C21N FA8B16N FA8A80N FA8A81N FA8A83N FA8A84N FA8A85N FA8A86N FA8A87N FA8A90N FA8A91N FA8A94N FA8A95N FA8A60N FA8A61N FA8A64N FA8A65N FA8A70N FA8A71N FA8A74N FA8A75N FA8A00N FA8A01N FA8A40N FA8A41N FA8A27N FA8A37N FA8A39N FA8A12N FA5680N FA5681N',a,'Green-mode PWM controller IC.'),('FA1C20N FA1B00N FA1B10N FA1B20N FA1A00N FA1A01N FA1A10N FA1A11N FA1A50N FA1A60N FA1A21N FA5590N FA5591N FA5696N FA5612N FA5613N',b,'Power-factor correction IC.'),('FA6C60N FA6C61N FA6C62N FA6C63N FA6C64N FA6B19N FA6B20N FA6B22N FA6A00AN FA6A10N FA6A11N FA6A30N FA6A31N',c,'LLC resonant controller IC.')]:
 for name in names.split():products.append(p(name,desc,src,life='commercial',typ='product',sector='semiconductors',sub='chip_design',roles=['developer','manufacturer']))
co=dict(company_id='cmp_2c33c39d-0af2-4555-b8d2-808c6be581db',products=products,evidence=[a,b,c],status='partial',coverage_note='Sixty-one exact power-control IC models from three current official product tables. No invented suffix variants or parameter assumptions. Partial: remaining general PWM/quasi-resonant/driver ICs, IGBT and SiC modules/discretes, pressure sensors, storage systems and other qualifying offerings remain.')
(out/'batch-0352.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
