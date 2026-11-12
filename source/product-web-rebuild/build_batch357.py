from research_helpers import *
a=ev('https://www.amgen.com/products','Official U.S. product index reviewed. Regional catalogue, not evidence of worldwide rights or every indication. Corlanor and Sensipar have retained label links without active brand websites; current availability not asserted.')
urls=json.loads((out/'amgen-label-urls.json').read_text())
ingredients={'ACTIMMUNE':'interferon gamma-1b','AIMOVIG':'erenumab-aooe','AMJEVITA':'adalimumab-atto','ARANESP':'darbepoetin alfa','AVSOLA':'infliximab-axxq','BKEMV':'eculizumab-aeeb','BLINCYTO':'blinatumomab','CORLANOR':'ivabradine','ENBREL':'etanercept','EPOGEN':'epoetin alfa','EVENITY':'romosozumab-aqqg','IMDELLTRA':'tarlatamab-dlle','IMLYGIC':'talimogene laherparepvec','KANJINTI':'trastuzumab-anns','KRYSTEXXA':'pegloticase','KYPROLIS':'carfilzomib','LUMAKRAS':'sotorasib','MVASI':'bevacizumab-awwb','NEULASTA':'pegfilgrastim','NEUPOGEN':'filgrastim','NPLATE':'romiplostim','OTEZLA':'apremilast','PARSABIV':'etelcalcetide','PAVBLU':'aflibercept-ayyh','PROCYSBI':'cysteamine bitartrate','PROLIA':'denosumab','RAVICTI':'glycerol phenylbutyrate','REPATHA':'evolocumab','RIABNI':'rituximab-arrx','SENSIPAR':'cinacalcet','TAVNEOS':'avacopan','TEPEZZA':'teprotumumab-trbw','UPLIZNA':'inebilizumab-cdon','VECTIBIX':'panitumumab','XGEVA':'denosumab'}
shared={'TEPEZZA':'prd_9479855b-759d-40e2-8d4e-5a6708910b00','UPLIZNA':'prd_350cc3a3-28f6-46f6-91c7-08694ee32c24'}
products=[];sources=[a]
for name,ingredient in ingredients.items():
 assert (out/f'amgen-label-{name}-firstpage.txt').exists(),name
 src=ev(urls[name],'Linked official prescribing label first page reviewed for exact brand and active ingredient. Label availability does not establish every current indication or commercial availability.')
 sources.append(src)
 item=p(name,f'{ingredient} prescription medicine.',src,life='unknown' if name in ['CORLANOR','SENSIPAR'] else 'commercial',typ='product',roles=['commercial_partner'],territory='US',evidence=[a,src])
 if name in shared:item['product_id']=shared[name]
 products.append(item)
src=ev('https://investors.amgen.com/news-releases/news-release-details/tezspirer-delivered-histologic-remission-and-symptom-improvement','October 20, 2026 issuer release confirms TEZSPIRE ingredient and Amgen/AstraZeneca collaboration. Eosinophilic-esophagitis phase-three results not treated as approval.')
products.append(p('TEZSPIRE','Tezepelumab-ekko antibody medicine.',src,life='commercial',typ='product',roles=['commercial_partner'],territory='US',evidence=[a,src]));sources.append(src)
src=ev(urls['OTEZLA'],'Current official label explicitly names OTEZLA XR extended-release tablets alongside immediate-release OTEZLA; distinct branded formulation, not a new active molecule.')
products.append(p('OTEZLA XR','Extended-release apremilast tablets.',src,life='commercial',typ='product',roles=['commercial_partner'],territory='US'));sources.append(src)
co=dict(company_id='cmp_2c573fa1-77b3-4119-8f11-495191d59646',products=products,evidence=sources,status='partial',coverage_note='37 U.S.-listed branded medicines/formulations linked, reusing existing TEPEZZA and Uplizna identities. Commercial-partner role restricted to US; original development or worldwide ownership not inferred from portfolio listing. Corlanor/Sensipar lifecycle unknown because retained labels do not confirm current sales. OTEZLA XR distinct formulation, not novel molecule; denosumab brands retained separately. Partial: worldwide brands, development pipeline, historical/divested medicines, detailed indication-specific contexts and licensing histories remain. No automated OpenAI retrieval.')
(out/'batch-0357.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
