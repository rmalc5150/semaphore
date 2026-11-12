from research_helpers import *
a=ev('https://www.bio-works.com/product/','Current manufacturer catalogue names WorkBeads resins and GoBio column/kit families. Duplicate GoBioMiniNTA cards not treated as separate products without verified differences. Exact pack-size SKUs not inferred.')
b=ev('https://www.bio-works.com/product/sec-resin/','Current manufacturer lists three distinct WorkBeads40 SEC pore-range resins plus MacroSEC and Dsalt. Separate matrix variants not combined into a single unspecified40SEC product.')
c=ev('https://www.bio-works.com/hubfs/New%20documents%20%2801052026%29/DS40300010BD%20WorkBeads%20SEC%20GoBio%20Prepacked%20columns.pdf?hsLang=en','2026 manufacturer data sheet explicitly lists four named SEC resins in GoBioPrep16x600 120mL and26x600 320mL formats. Descriptive resin/format labels are not invented manufacturer part numbers; inconsistent prose saysfive but onlyfour named,so nofifth inferred.')
d=ev('https://www.bio-works.com/hubfs/Documents/MM10001003BB%20Bio-Works%20Product%20catalogue.pdf','Historical manufacturer catalogue distinguishes WorkBeads40/1000ACT and40/10000ACT matrices. Pack volumes grouped,not separate formulation products. Current individual variant availability unresolved.')
e=ev('https://www.bio-works.com/products/workbeads-nimac/','Current manufacturer confirms NiMAC resin with strongly bound nickel; no invented metal-free or particle-size variants.')
products=[]
bulk=['WorkBeads NTA','WorkBeads NiMAC','WorkBeads Macro SEC','WorkBeads Dsalt','WorkBeads affimAb Edge','WorkBeads affimAb','WorkBeads 40S','WorkBeads 40Q','WorkBeads 40 TREN','WorkBeads 40 DEAE','WorkBeads 100S','WorkBeads 100Q','WorkBeads 40/100 SEC','WorkBeads 40/1000 SEC','WorkBeads 40/10000 SEC']
for name in bulk:
 source=b if 'SEC' in name or name.endswith('Dsalt') else e if name=='WorkBeads NiMAC' else a
 products.append(p(name,'Manufacturer-listed agarose chromatography resin or resin family; bulk pack volumes grouped.',source,'commercial',roles=['manufacturer'],typ='product',sub='research_tools',attributes={'format':'bulk_resin','exact_pack_SKUs':'not_reconciled'},evidence=[a,source] if source!=a else [a]))
for name in ['WorkBeads 40/1000 ACT','WorkBeads 40/10000 ACT']:
 products.append(p(name,'Distinct historically catalogued pre-activated chromatography resin; current exact variant availability unverified.',d,'unknown',roles=['manufacturer'],typ='product',sub='research_tools',attributes={'format':'bulk_resin'},evidence=[a,d]))
mini=['Dsalt','TREN','S','Q','Peptide Purification Kit','NTA','NiMAC','IEX Screening Kit','DEAE','affimAb Edge','affimAb','ACT']
for name in mini:
 products.append(p('GoBio Mini '+name+' family','Manufacturer-listed prepacked chromatography column or screening-kit family; exact volume/resin/SKU variants unverified.',a,'commercial',roles=['manufacturer'],typ='product',sub='research_tools',attributes={'format':'screening_kit_family' if 'Kit' in name else 'prepacked_column_family','exact_variants':'not_reconciled'}))
for resin in ['WorkBeads 40/100 SEC','WorkBeads 40/1000 SEC','WorkBeads 40/10000 SEC','WorkBeads Macro SEC']:
 for fmt,vol in [('16x600',120),('26x600',320)]:
  products.append(p('GoBio Prep '+resin+' '+fmt,'Manufacturer-documented prepacked SEC column configuration; distinct from bulk resin.',c,'commercial',roles=['manufacturer'],typ='product',sub='research_tools',attributes={'resin':resin,'column_format':fmt,'bed_volume_ml':vol,'identity_label':'descriptive_configuration_not_part_number'}))
co=company('BIO-WORKS TECHN. AB',products,[a,b,c,d,e],'37 resin/column/kit identities or explicitly scoped families entered. Bulk pack sizes grouped; eight distinct SEC prepacked configurations verified in2026data sheet. DuplicateNTA card not doubled. Individual product pages partly unavailable403/cachemiss; no access restrictions bypassed. Need exact article numbers,Mini resin/volume variants,GoBioScreen/Prod/otherPrep formats,remainingkits and currentACTvariantavailability. Do not treat this partial catalogue review as complete.')
(out/'batch-0159.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
