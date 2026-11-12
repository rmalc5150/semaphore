from research_helpers import *
a=ev('https://www.almirall.com/investors/reports/annual/2025/transforming-patients-live/our-portfolio/','Issuer portfolio names ten dermatology medicines; regional availability varies. Conflicting Solaraze description not adopted as ingredient identity.')
b=ev('https://www.almirall.com/innovation/pipeline','Current pipeline identifies seven distinct early-stage molecular programmes. Multiple indications for same antibody/fusion protein consolidated, not separate molecules.')
c=ev('https://backend.almirall.com/sites/default/files/2026-04/EN-EINF-2025-Almirall.pdf','2025 issuer report identifies regional rights: Ebglyss Europe Lilly,Ilumetri Europe SunPharma,Wynzora Europe MC2; ISB880 from Ichnos andSIM0278 from Simcere exChina. Not original ownership of partner portfolios.')
d=ev('https://www.almirall.com/news-media/newsroom/almirall-licenses-anti-il-21-monoclonal-antibody-novo-nordisk-develop-it-first','Issuer confirms antiIL21 molecule NN8828 exclusive field-specificgloballicence fromNovoNordisk.')
e=ev('https://www.almirall.com/news-media/newsroom/almiralls-q1-2024-results-almirall-delivers-strong-start-2024-q1-net-sales','Issuer confirms EloxxZKN013 licensed for rare dermatology. No unsupported mapping to otherALMcode.')
f=ev('https://backend.almirall.com/sites/default/files/2026-04/ENG-PRINT-EXECUTIVE-SUMMARY_2025_FINAL-2026-02-23-21-46.pdf','Efinaconazole Germany approvalAugust2025; launch plan in progress. Approval/planned2026launchnotproofactualcommercialavailability.')
products=[]
for name,desc,roles,territory in [
 ('Ebglyss','Lebrikizumab anti-IL13 medicine for atopic dermatitis.',['licensee'],'Europe'),
 ('Cordran Tape','Flurandrenolide medicated tape.',['commercial_partner'],'unknown'),
 ('Ilumetri','Tildrakizumab anti-IL23 medicine for psoriasis.',['licensee'],'Europe'),
 ('Wynzora cream','Calcipotriene and betamethasone dipropionate topical medicine.',['licensee'],'Europe'),
 ('Skilarence','Dimethyl fumarate oral psoriasis medicine.',['commercial_partner'],'unknown'),
 ('Klisyri','Tirbanibulin topical actinic keratosis medicine.',['commercial_partner'],'unknown'),
 ('Actikerall','Fluorouracil and salicylic acid topical medicine.',['commercial_partner'],'unknown'),
 ('Solaraze','Topical actinic keratosis medicine; active ingredient not normalized from inconsistent summary page.',['commercial_partner'],'unknown'),
 ('Seysara','Sarecycline oral acne medicine.',['commercial_partner'],'unknown'),
 ('Ciclopoli','Ciclopirox topical nail antifungal medicine.',['commercial_partner'],'unknown')]:
 products.append(p(name,desc,a,'commercial',typ='product',roles=roles,territory=territory,evidence=[a,c] if roles==['licensee'] else [a],aliases=['Winxory'] if name=='Wynzora cream' else []))
products.append(p('Almirall efinaconazole topical medicine','European antifungal medicine with national approval; reviewed source does not verify actual launch or European brand identity.',f,typ='product',roles=['licensee'],territory='Europe'))
for name,desc,source,aliases,territory in [
 ('Almirall anti-IL1RAP antibody','PhaseII dermatology programme licensed fromIchnos; oncologyrightsnotincluded.',c,['ISB880'],'Worldwide, licensed dermatology fields'),
 ('NN-8828','AntiIL21 antibody in PhaseII dermatology development; field-specificrights.',d,[],'Worldwide, licensed dermatology fields'),
 ('SIM0278','IL2 mutant fusion protein,PhaseII acrossskin diseases; same molecule acrossindications.',c,['ALM223'],'Worldwide excluding Greater China'),
 ('ZKN-013','Licensed oral readthrough-inducer programme forrare dermatology. OtherALMcodeequivalenceunverified.',e,[],'Worldwide, licensed fields'),
 ('Almirall anti-IL13/OX40L bispecific antibody','PhaseI atopicdermatitis programme.',b,[],'Worldwide'),
 ('Almirall oral SMOL for Th2-driven disease','Preclinical small-molecule programme; exactchemicalcodeundisclosed.',b,[],'Worldwide'),
 ('Almirall mRNA-LNP skin-cancer programme','Preclinical messengerRNA/lipidnanoparticle programme.',b,[],'Worldwide')]:
 products.append(p(name,desc,source,'development' if 'Preclinical' not in desc else 'research',roles=['licensee'] if source in [c,d,e] else ['developer'],aliases=aliases,territory=territory,evidence=[source,b] if source!=b else [b]))
co=company('Almirall',products,[a,b,c,d,e,f],'Eighteen current dermatology medicines/programmes entered. Ten marketed medicines,efinaconazole withunverifiedactualEuropeanlaunch,andseven molecularprogrammes;indicationextensionstudiesnotduplicateproducts. Partnerregional/fieldlicences retained;otherALMcodeequivalencesunverified. Needfull50plusproductcountrycatalogue,non-dermatologymedicines,legacy/deprioritizedprogrammes,exactdosageforms/strengthsandcurrentefinaconazolebrand/launchverification. Currentpipelinephaseupdatesusedoverolderforecasts;progressnotcompletion. Partial.')
(out/'batch-0180.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
