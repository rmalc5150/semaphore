from research_helpers import *
rows=json.loads((out/'enzo-reviewed-page1.json').read_text())+json.loads((out/'enzo-reviewed-elisa.json').read_text())
groups={}
for r in rows:
 if not r['variants'] or any(v.get('item_brand')!='Enzo' for v in r['variants']):continue
 key=r['sku'].replace('ADI-901-','ADI-900-')
 groups.setdefault(key,[]).append(r)
ps=[];es=[]
for sku,rs in groups.items():
 r=next((x for x in rs if x['sku']==sku),rs[0]);name=r['name'];is_assay='ELISA' in name
 evidence=[ev(x['url'],'Current Enzo-branded public catalogue listing reviewed; pack sizes grouped under one product identity. Research reagent offering, without clinical diagnostic or therapeutic approval claim.') for x in rs];es+=evidence
 attrs={'catalogue_name':name,'manufacturer_catalogue_codes':[x['sku'] for x in rs],'packaging_options':[v for x in rs for v in x['variants']],'intended_use':'research reagent; clinical approval not established'}
 if r.get('features'):attrs['manufacturer_assay_features']=r['features']
 ps.append(p('Enzo '+sku+' '+name,('Research ELISA immunoassay kit for '+name.replace(' ELISA kit','')+'.') if is_assay else 'Enzo-branded biological research reagent: '+name+'.',evidence[0],'commercial',roles=['commercial_partner'],typ='product',sub='research_tools',attributes=attrs,evidence=evidence))
cs=[company('Enzo Biochem Inc',ps,es,'Reviewed 15 Enzo-branded first-page reagents and 13 distinct inflammation ELISA assays, grouping three five-plate packs with corresponding single-plate identities. One listing without brand/pack verification deferred. Current catalogue listings establish commercial offering, not stock availability or clinical approval. Large remaining reagent, antibody, assay, probe and platform catalogue requires further research; 2026 Axxora marketplace removals must be excluded unless current offering verified.')]
(out/'batch-0113.json').write_text(json.dumps({'companies':cs},indent=2));print(len(ps))
