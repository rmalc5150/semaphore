from research_helpers import *
R=ev('https://www.diatheva.com/biotech-company-and-life-sciences-partner/','Diatheva confirms acquisition by SOL Group in 2012 and current group membership. Customer CDMO drugs are not attributed to SOL.')
ps=[]
sets=[('assays','Clinical diagnostic assay','diagnostics'),('assays_environment','Food/environment testing or extraction kit','diagnostics'),('assays_veterinary','Veterinary assay or extraction kit','diagnostics'),('reagents','Biological research reagent','research_tools')]+[(f'reagents-{i}','Biological research reagent','research_tools') for i in range(2,6)]
for key,desc,sub in sets:
 d=json.loads((out/f'diatheva-{key}.json').read_text())
 for row in d['data']:
  code=row['codice'].strip();E=ev(row['permalink'],'Official public catalogue product identity and manufacturer catalogue code reviewed; detailed regulatory status not inferred from listing.')
  n='Diatheva '+row['title']
  if key.startswith('reagents'):n+=' ['+code+']'
  ps.append(p(n,desc+': '+row['title']+'.',E,'commercial',roles=['commercial_partner'],typ='product',sub=sub,evidence=[E,R],attributes={'brand':'Diatheva','catalogue_code':code,'catalogue_size_as_listed':row['size_small'],'catalogue_targets':[x['name']for x in row['categories']],'catalogue_detail_url':row['permalink'],'evidence_scope':'Official catalogue name, code, pack size and target; individual specifications and regulatory status require further review.'}))
cs=[company('SOL S.p.A',ps,[R],'Current Diatheva clinical (2), environmental (7), veterinary (12) and five reagent catalogue pages reviewed. Reagent catalogue codes preserve distinct ordering identities; assay pack sizes remain attributes. SOL link is group commercial association, not an assertion parent invented subsidiary reagents. Other SOL biotech subsidiaries, proprietary therapeutic antibodies, medical gases and detailed per-product specifications remain to research.')]
(out/'batch-0063.json').write_text(json.dumps({'companies':cs},indent=2));print(len(ps))
