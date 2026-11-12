from research_helpers import *
P=ev('https://www.biohaven.com/pipeline/','Named clinical and preclinical pipeline reviewed; multiple indications consolidated by molecule. Later dated issuer updates override stale graphical phase labels.')
Q=ev('https://ir.biohaven.com/news-releases/news-release-details/biohaven-reports-recent-business-developments-and-second-quarter','August 2026 update confirms BHV1300 phase3, BHV1400 phase1b, taldefgrobep obesity phase2, BHV8100 first-in-human dosing and BHV8000 phase2/3.')
H=ev('https://www.sec.gov/Archives/edgar/data/1935979/000193597926000077/bhvn-20260904.htm','September4 2026 partial clinical hold pauses new BHV7000 enrollment; existing participant treatment and enrolled RISE3 trial continue. Not marketed or discontinued.')
L=ev('https://ir.biohaven.com/news-releases/news-release-details/biohaven-and-sk-biopharmaceuticals-enter-strategic-global','August26 2026 global Kv7 license to SK; Biohaven retains development relationship and specified economics.')
Y=ev('https://ir.biohaven.com/news-releases/news-release-details/biohaven-advances-new-class-precision-immunology-therapies-first','BHV1300 licensed exclusively from Yale.')
O=ev('https://ir.biohaven.com/news-releases/news-release-details/biohaven-enters-strategic-licensing-agreement-ono-pharma','October8 2026 regional IgG-degrader license to Ono covers BHV1300/1310/1320; does not transfer worldwide ownership.')
A=ev('https://ir.biohaven.com/static-files/8eb75c9f-8dfc-4752-8578-438c2dc867a7','2025 annual report filed March2026 confirms troriluzole November2025 CRL and requested FDA meeting/appeal, not approval.')
ps=[]
for n,d,stage,life in [('BHV-1300','IgG degrader.','Phase 3','development'),('BHV-1400','Gd-IgA1 degrader.','Phase 1b','development'),('BHV-1600','Beta1 autoantibody degrader.','Phase 1','development'),('BHV-8000','Brain-penetrant TYK2/JAK1 inhibitor.','Phase 2/3','development'),('Opakalim','Kv7 potassium-channel activator.','Phase 2/3','development'),('BHV-2100','TRPM3 antagonist.','Phase 2','development'),('Taldefgrobep alfa','Myostatin inhibitor.','Phase 2','development'),('BHV-1510','TROP2-directed antibody-drug conjugate.','Phase 1b','development'),('BHV-1530','FGFR3-directed antibody-drug conjugate.','Phase 1b','development'),('BHV-1310','IgG degrader.','Preclinical','research'),('BHV-1320','Immune-disease degrader.','Preclinical','research'),('BHV-1450','IgG4 degrader.','Preclinical','research'),('BHV-1420','PLA2R autoantibody degrader.','Preclinical','research'),('BHV-1440','TSHR autoantibody degrader.','Preclinical','research'),('BHV-6500','Proinsulin autoantibody degrader.','Preclinical','research'),('BHV-1490','IgM degrader.','Preclinical','research'),('BHV-8100','PKM2 modulator.','Phase 1','development'),('BHV-1955','Intranasal oxytocin programme.','Preclinical','research')]:
 als=['BHV-7000']if n=='Opakalim'else ['BHV-2000']if n=='Taldefgrobep alfa'else []
 e=[P]
 if n in ['BHV-1300','BHV-1400','BHV-8000','Taldefgrobep alfa','BHV-1510','BHV-1530','BHV-8100']:e.append(Q)
 if n=='BHV-1300':e.extend([Y,O])
 if n in ['BHV-1310','BHV-1320']:e.append(O)
 if n=='Opakalim':e.extend([H,L])
 attr={'reported_stage':stage}
 if n=='Opakalim':attr['enrollment_status']='new enrollment partially held by FDA September 4 2026; existing treatment continues'
 ps.append(p(n,d,P,life,aliases=als,attributes=attr,evidence=e))
ps.append(p('Troriluzole','Investigational glutamate modulator; SCA regulatory application received CRL.',A,aliases=['BHV-4157'],attributes={'regulatory_status':'November 2025 CRL; appeal process requested as of March 2026','current_development_status':'not listed on current pipeline; subsequent status requires followup'}))
cs=[company('Biohaven Ltd.',ps,[P,Q,H,L,Y,O,A],'18 named current pipeline molecules plus historical troriluzole captured. September2026 enrollment hold and August2026 clinical updates override stale phase graphics. SK global Kv7 and Ono regional degrader transactions documented. Historical discontinued/licensed programmes, technology platforms and 2022 separation rights need followup; Pfizer-acquired CGRP assets not automatically attributed to this entity.')]
(out/'batch-0050.json').write_text(json.dumps({'companies':cs},indent=2));print(len(ps))
