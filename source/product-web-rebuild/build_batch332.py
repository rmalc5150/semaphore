from research_helpers import *
a=ev('https://investors.vir.bio/news/news-details/2024/Vir-Biotechnology-Provides-Corporate-Update-and-Reports-First-Quarter-2024-Financial-Results/default.aspx','Historical influenza, HPV and respiratory antibody programmes; old forecast not treated as actual IND or current status.')
b=ev('https://investors.vir.bio/news/news-details/2023/Vir-Biotechnology-Announces-First-Participant-Dosed-in-New-Phase-1-Trial-Evaluating-VIR-1388-an-Investigational-T-Cell-Vaccine-for-the-Prevention-of-HIV-09-20-2023/default.aspx','VIR-1388 and predecessor VIR-1111 are distinct HIV vaccine candidates.')
c=ev('https://us.gsk.com/en-us/media/press-releases/gsk-and-vir-biotechnology-announce-sotrovimab-vir-7831-receives-emergency-use-authorization-from-the-us-fda/','Partner explicitly equates sotrovimab/VIR-7831 and VIR-7832/GSK4182137; historical authorization not current authorization claim.')
d=ev('https://investors.vir.bio/news/news-details/2021/Preclinical-Data-Demonstrate-Sotrovimab-Retains-Activity-Against-Key-Omicron-Mutations-New-SARS-CoV-2-Variant-12-02-2021/default.aspx','Partner product brand Xevudy explicitly sotrovimab.')
products=[]
for name,desc in [('VIR-2482','Historical influenza-A antibody.'),('VIR-2981','Historical influenza-A/B neuraminidase antibody.'),('VIR-1949','Historical HPV therapeutic vaccine.'),('VIR-7229','Historical coronavirus antibody.'),('VIR-8190','Historical RSV/metapneumovirus antibody.')]:products.append(p(name,desc,a))
for name in ['VIR-1388','VIR-1111']:products.append(p(name,'Historical investigational HCMV-vector HIV vaccine.',b))
products.append(p('VIR-7832','Historical coronavirus antibody.',c,aliases=['GSK4182137']))
r=json.loads((out/'batch-0331.receipt.json').read_text())
s=next(x for x in r['manifest']['companies'][0]['products'] if x['canonical_name']=='Sotrovimab')
products.append(p('Sotrovimab','Historical antiviral antibody.',c,aliases=['VIR-7831','Xevudy'],product_id=s['inserted_product_id'],evidence=[c,d]))
co=dict(company_id='cmp_2b5d726d-6d25-4703-9889-fa4a9721478e',products=products,evidence=[a,b,c,d],status='partial',coverage_note='Eight additional historical candidate molecules and sotrovimab aliases added to existing identity; 17 total product/platform identities recorded. Current five named pipeline molecules recorded previously. Historical candidates remain lifecycle unknown pending current sponsor/discontinuation checks; clinical/IND forecasts not treated as achieved. Partial: historical programme disposition, uncoded HIV/tuberculosis/malaria projects, geographic authorizations and predecessor platforms require further review.')
(out/'batch-0332.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products)-1,'new, 1 alias enrichment')
