from research_helpers import *
C=ev('https://www.immutep.com/prima-biomed-changes-its-name-to-immutep-ltd/','Issuer confirms Prima BioMed renamed Immutep; historical vaccine licensed out, not a separate issuer invention.')
F=ev('https://www.sec.gov/Archives/edgar/data/1506184/000119312526379062/d435000dex991.htm','FY2026 issuer: efti and IMP761 remain development assets; TACTI-004 trial closure does not end entire efti program. LAG525 program stopped in 2022; Novartis agreement ended August 2026. IMP731-related returned asset under review. Humanised derivatives kept distinct from precursor antibodies.')
H=ev('https://www.immutep.com/files/content/investor/financial/1859243.pdf','Historical issuer names precursor antibodies IMP701 and IMP731 alongside IMP321 and IMP761; acquired Immutep subsidiary portfolio.')
V=ev('https://www.immutep.com/files/content/investor/investor-update/2016/IU-Edition-17.pdf','CVac historical cell-based vaccine, licensed to Sydys; ongoing present development not assumed.')
G=ev('https://www.immutep.com/dw/uploads/2025/06/Half-Year-Report-ended-31-December-2023.pdf','GSK2831781 humanized derivative of IMP731; rights transfer effective May 30 2024. Efti also designated EOC202 by territorial partner.')
ps=[p('Eftilagimod alfa','Investigational soluble LAG-3 immunotherapy protein.',F,'development',aliases=['IMP321','Efti','EOC202'],evidence=[F,G]),p('IMP761','Investigational agonist LAG-3 antibody.',F,'development'),p('IMP701','Historical precursor antagonist LAG-3 antibody.',H),p('Ieramilimab','Humanised LAG-3 antagonist antibody developed from IMP701.',F,'discontinued',roles=['owner'],aliases=['LAG525']),p('IMP731','Historical precursor depleting LAG-3 antibody.',H),p('GSK2831781','Humanised LAG-3 depleting antibody derived from IMP731.',G,roles=['owner'],evidence=[F,G]),p('CVac','Historical dendritic-cell therapeutic cancer vaccine.',V)]
for x in ps:
 for a in x['aliases']:
  if a['alias'] in ['Eftilagimod alfa','Ieramilimab']:a['alias_type']='generic_name'
companies=[company('Prima Biomed Ltd',ps,[C,F,H,V,G],'Renamed issuer, current programs, humanised derivatives versus precursor antibodies and licensed historical vaccine reviewed. Earlier pre-LAG3 assets, latest returned-rights status and formulation inventory remain unresolved.')]
(out/'batch-0015.json').write_text(json.dumps({'companies':companies},indent=2))
