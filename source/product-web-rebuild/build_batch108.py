from research_helpers import *
rows=json.loads((out/'abb-reviewed-large-variants.json').read_text());ps=[];es=[]
S=ev('https://new.abb.com/news/detail/137499/abb-expands-automation-offering-with-acquisition-of-rotork','July2026 robotics sale to SoftBank described as pending; parent commercial brand relationship used without assertion of present legal ownership.')
for r in rows:
 e=ev(r['url'],'Current manufacturer available-variants table: exact model, rated payload and reach directly reviewed; LID configuration distinct from standard model.');es.append(e)
 name=r['model'].replace('3.1LID','3.1 LID')
 attrs={'manufacturer_model_as_listed':r['model'],'rated_payload_kg':r['payload_kg'],'reach_m':r['reach_m'],'robot_type':'articulated','company_relationship_scope':'ABB-branded robotics portfolio; commercial relationship; current SoftBank closing unverified'}
 if 'LID' in name:attrs['integrated_dressing']='LID'
 ps.append(p('ABB '+name,'Large industrial articulated robot variant.',e,'commercial',roles=['commercial_partner'],typ='product',sector='robotics',sub='industrial_robotics',attributes=attrs,evidence=[e,S]))
cs=[company('ABB Ltd',ps,es+[S],'Forty-eight additional exact large-robot variants reviewed across5710/5720/6710/6720/6730/6740/7710/7720/6790; previous68 robot variants retained. Palletizing/paint robots, older/current remaining arms including7710SFX, AMRs, controllers/software/application cells, other semiconductor/storage products and latest SoftBank closing status remain to research.')]
(out/'batch-0108.json').write_text(json.dumps({'companies':cs},indent=2));print(len(ps))
