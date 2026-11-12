from research_helpers import *
a=ev('https://tymeinc.com/about-tyme/tyme-overview/default.html','Legacy company overview names SM-88 oral, distinct injectable SM-88i, TYME-18 and TYME-19. Historical website not current clinical-activity evidence.')
b=ev('https://s22.q4cdn.com/265040820/files/doc_presentations/2021/11/TYME-Investor-Presentation-November-2021.pdf','Historical issuer pipeline also names TYME-T3 tumour-targeting technology.')
c=ev('https://www.faegredrinker.com/en/services/experience/2022/9/tyme-technologies-completes-merger-with-syros-pharmaceuticals','Transaction counsel confirms Tyme merger with Syros closed September 16, 2022. No assumption that acquired programmes continued unchanged.')
products=[]
for name,desc in [('SM-88','Oral investigational cancer-metabolism therapy.'),('SM-88i','Distinct injectable formulation of SM-88.'),('TYME-18','Intratumoral metabolism-directed oncology candidate.'),('TYME-19','Historical antiviral candidate for SARS-CoV-2.')]:
 products.append(p(name,desc,a))
products.append(p('TYME-T3','Historical tumour-targeting technology.',b,typ='technology'))
co=dict(company_id='cmp_1800757e-f17c-4abb-a607-bc058d0abce5',products=products,evidence=[a,b,c],status='partial',coverage_note='Five named legacy programmes/technologies recorded; injectable and oral SM-88 distinct formulations. Partial: current rights, SM-88 programme status after merger, later outlicensing or termination and Tyme subsidiary continuity need review. Unknown lifecycle avoids representing old company marketing as active 2026 trials. No writes to currently ineligible Syros parent company.')
(out/'batch-0249.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
