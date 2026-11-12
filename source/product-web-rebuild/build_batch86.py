from research_helpers import *
S=ev('https://www.abbott.com/en-us/products-solutions/product-list','Current parent catalogue: regional availability varies. Diagnostic identities reviewed; no global approval inferred. Umbrella-only Alinity/ARCHITECT entries not duplicated.')
A=ev('https://www.corelaboratory.abbott/us/en/offerings/brands/architect.html','Nine current ARCHITECT models and listed maximum throughputs.')
C=ev('https://www.corelaboratory.abbott/us/en/offerings/brands/alinity/alinity-ci-series.html','Alinity c/i modules and integrated ci system specifications.')
H=ev('https://www.corelaboratory.abbott/us/en/offerings/brands/alinity/Alinity-h-hematology-system.html','Alinity hq analyser and hs slide system, distinct modules.')
F=ev('https://www.globalpointofcare.abbott/us/en/product-details/afinion2-analyzer-us.html','Afinion2 current analyser and ACR/HbA1c assays; regional ordering codes preserved as configurations, not duplicate devices.')
ps=[]
def add(n,d,s=S,attrs={}):ps.append(p('Abbott '+n,d,s,'commercial',roles=['commercial_partner'],typ='product',sub='diagnostics',attributes=attrs))
for n in ['ACCELERATOR','AlinIQ','Alinity m','Alinity mp','Alinity s','CELL-DYN','Cholestech LDX','CP 3000','Determine HIV-1/2 Ag/Ab Combo','GLP systems Track','ID NOW','i-STAT 1','i-STAT Alinity','i-STAT Wireless','m2000','PathVysion','Piccolo Xpress','RALS','RealTime PCR','simpli-COLLECT STI Test','simpli-COLLECT HPV Collection Kit','ThermoBrite','UroVysion','VIP 2000','Vysis CLL']:
 add(n,'Diagnostic product or named family.',attrs={'identity_scope':'named current catalogue entry; further models/assays require review'})
add('BinaxNOW COVID-19/Flu A&B Combo Self Test','Self-use diagnostic test.')
add('BinaxNOW COVID-19/Flu A&B professional test','Professional-use diagnostic test.')
for n,t in [('ci4100',900),('ci8200',1400),('ci16200',2000),('c4000',800),('c8000',1200),('c16000',1800),('i1000SR',100),('i2000SR',200),('i4000SR',400)]:add('ARCHITECT '+n,'Clinical laboratory analyser.',A,{'maximum_throughput_tests_per_hour':t})
for n,t in [('c',1350),('i',200),('ci-series',1550)]:add('Alinity '+n,'Clinical chemistry/immunoassay system.',C,{'maximum_throughput_tests_per_hour':t})
add('Alinity hq','Hematology analyser.',H)
add('Alinity hs','Hematology slide preparation system.',H)
add('Afinion 2','Point-of-care multi-assay analyser.',F,{'regional_order_codes':{'US_CLIA_waived':'1116985','US_moderate_complexity':'1116970','EU_worldwide':'1116770'}})
add('Afinion ACR','Urine albumin/creatinine assay.',F)
add('Afinion HbA1c','Whole-blood glycated haemoglobin assay.',F)
cs=[company('Abbott Laboratories',ps,[S,A,C,H,F],'44 named diagnostic instruments/assays/software/families reviewed, including exact ARCHITECT models and Alinity modules. Parent family umbrella duplicates avoided; higher catalogue breadth remains partial. Full assay/reagent menus, point-of-care devices, pharmaceuticals, regional formulations, medical devices, CGM and subsidiary catalogues require research. No all-company completion claim.')]
(out/'batch-0086.json').write_text(json.dumps({'companies':cs},indent=2));print(len(ps))
