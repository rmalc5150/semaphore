from research_helpers import *
base='https://www.macom.com/products/optical/photodiodes/'
rows=[('10g-apd-photodiodes','Avalanche photodiode.','32448-02 32445-01 32447-02 MARP-FSAPD10B MARP-FSAPD10A 32445-02'),('25g-apd-photodiodes','Avalanche photodiode.','32392-03 32411-03 32411-04 32412-03 32412-04 32391-03'),('50_100g-pam4-pin-photodiodes','Optical photodiode.','32437-01 MARP-FP56-011D-P MARP-FP28-024D-P MARP-FP56-024D-P 32439-06 MARP-BA56 MARP-FP28-011D-P MARP-FP56-014D-P MARP-FMP100 32439-01'),('200g-pam4-pin-photodiodes','PIN photodiode.','MARP-BP112')]
products=[];evidence=[]
for path,desc,names in rows:
 src=ev(base+path,'All explicitly identified current photodiode entries reviewed; mounted/carrier variants retained only where distinct manufacturer identifiers given.');evidence.append(src)
 for name in names.split():products.append(p('MACOM '+name,desc,src,life='commercial',typ='product',sector='semiconductors',sub='chip_design'))
co=dict(company_id='cmp_2febb457-b6e4-4447-b43a-77040292440f',products=products,evidence=evidence,status='partial',coverage_note='142 MACOM identifiers total: prior 119 drivers/TIAs plus 23 exact photodiode offerings from four current categories. Manufacturer-designated carrier variants distinct; no invented configurations. Partial: laser, optical receiver/module, remaining optical/RF/power semiconductor categories, foundry platforms, legacy acquired products and detailed technical/availability metadata remain.')
assert len(products)==23
(out/'batch-0385.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
