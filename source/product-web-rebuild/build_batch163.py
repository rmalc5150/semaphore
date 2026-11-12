from research_helpers import *
a=ev('https://aionsilicon.com/about-us/history/','Current issuer confirms Sondrel rebranded AionSilicon2025 and historical Architecting-the-Future reference-platform launch. Corporate continuity established.')
b=ev('https://www.sondrel.com/assets/media/architecting-the-future-100-pr-final.pdf','Original issuer July2021 release verifies SFA100 semiconductor IP reference platform. Not a named mass-produced customer ASIC.')
c=ev('https://www.sondrel.com/assets/media/architecting-the-future-350a-pr-final.pdf','Original issuer June2021 release verifies SFA350A automotive reference platform and scalable SFA300 design. No entire Arm/NVIDIA/customer portfolio ownership inferred.')
d=ev('https://iconnect007.com/article/132712/sondrel-highlights-key-advantage-for-its-turnkey-asic-service-of-turning-concept-into-silicon/132715/ein','Issuer press-release reprint explicitly names five Architecting-the-Future platforms:SFA100/200/300/250A/350A. Exact current licence terms and availability unresolved.')
d['source']='issuer_press_release_reprint'
e=ev('https://aionsilicon.com/press-release/aion-silicon-to-participate-at-andes-risc-v-con/','2025 issuer describes confidential customer RISC-V accelerator design engagement. Design-service contract not proof company owns or offers customer chip as its own product.')
products=[]
for model in ['SFA 100','SFA 200','SFA 300','SFA 250A','SFA 350A']:
 source=b if model=='SFA 100' else c if model in ['SFA 300','SFA 350A'] else d
 products.append(p('Sondrel '+model+' IP reference platform','Historically offered semiconductor reference-design platform; current licence availability unverified.',source,'unknown',typ='technology',sector='semiconductors',sub='chip_design',aliases=[model.replace(' ','')],attributes={'scope':'IP_reference_platform_not_customer_ASIC','current_availability':'unverified'},evidence=[a,source,d] if source!=d else [a,d]))
co=company('SONDREL(HOLDINGS) LS-001',products,[a,b,c,d,e],'Five historically named semiconductor IP reference platforms entered. Sondrel/Aion continuity verified; confidential customerchips not represented as owned products. No family duplicate on top of five platform variants. Need current platform availability/licences,any newer named IP offerings and legacy Helium/Neon classification; service engagements and foundrypartnerships alone not distinct product SKUs.')
(out/'batch-0163.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
