from research_helpers import *
base='https://www.abb.com/global/en/areas/robotics/products/robots/'
ps=[];es=[]
def add(path,rows,kind='articulated',axis=None):
 e=ev(base+path,'Current manufacturer variant table reviewed; only listed model/payload/reach combinations imported.');es.append(e)
 for name,load,reach,extra in rows:
  attrs={'manufacturer_model':name,'robot_type':kind,'rated_payload_kg':load,'reach_m':reach,**extra}
  if axis:attrs['axes']=axis
  ps.append(p('ABB '+name,kind.capitalize()+' robot variant.',e,'commercial',roles=['commercial_partner'],typ='product',sector='robotics',sub='industrial_robotics',attributes=attrs))
add('scara-robots/irb-930',[('IRB 930-12/0.85',12,.85,{}),('IRB 930-12/1.05',12,1.05,{}),('IRB 930-22/1.05',22,1.05,{})],'SCARA')
add('scara-robots/irb-920t',[('IRB 920T-6/0.45',6,.45,{}),('IRB 920T-6/0.55',6,.55,{}),('IRB 920T-6/0.65',6,.65,{}),('IRB 920-6/0.45',6,.45,{}),('IRB 920-6/0.55',6,.55,{}),('IRB 920-6/0.65',6,.65,{})],'SCARA')
add('scara-robots/irb-910inv',[('IRB 910INV-3/0.35',3,.35,{}),('IRB 910INV-6/0.55',6,.55,{})],'SCARA')
add('articulated-robots/small-robots/irb-1010',[('IRB 1010',1.5,.37,{})])
add('articulated-robots/small-robots/irb-1090',[('IRB 1090',3.5,.58,{'application':'education'})])
add('articulated-robots/medium-robots/irb-1700id',[('IRB 1700ID-12/1.45',12,1.45,{}),('IRB 1700ID-10/1.65',10,1.65,{}),('IRB 1700ID-6/1.85',6,1.85,{})])
add('articulated-robots/medium-robots/irb-1700',[('IRB 1700-12/1.45',12,1.45,{}),('IRB 1700-10/1.65',10,1.65,{})])
add('articulated-robots/medium-robots/irb-1660id',[('IRB 1660ID-6/1.55',6,1.55,{}),('IRB 1660ID-4/1.55',4,1.55,{})])
add('articulated-robots/medium-robots/irb-1600',[('IRB 1600-6/1.2',6,1.2,{}),('IRB 1600-6/1.45',6,1.45,{}),('IRB 1600-10/1.2',10,1.2,{}),('IRB 1600-10/1.45',10,1.45,{})])
add('articulated-robots/medium-robots/irb-4600',[('IRB 4600-60/2.05',60,2.05,{}),('IRB 4600-45/2.05',45,2.05,{}),('IRB 4600-40/2.55',40,2.55,{}),('IRB 4600-20/2.50',20,2.51,{'source_name_and_reach_discrepancy':'Model label2.50; technical reach field2.51 retained as reported'})])
add('articulated-robots/small-robots/irb-1200-hygienic',[('IRB 1200-7/0.7 Hygienic',7,.7,{}),('IRB 1200-5/0.9 Hygienic',5,.9,{})])
add('collaborative-robots/single-arm-yumi',[('IRB 14050 Single-arm YuMi',.5,.559,{'payload_scope':'single arm'})],'collaborative',7)
add('collaborative-robots/dual-arm-yumi',[('IRB 14000 Dual-arm YuMi',.5,.559,{'payload_scope':'per arm','arms':2})],'collaborative',14)
S=ev('https://new.abb.com/news/detail/137499/abb-expands-automation-offering-with-acquisition-of-rotork','July2026 proposed robotics divestment still pending; no current parent legal ownership claim beyond evidenced commercial brand relationship.')
for x in ps:x['evidence'].append(S);x['attributes']['company_relationship_scope']='ABB-branded robotics portfolio; parent commercial relationship; current SoftBank closing status unverified'
cs=[company('ABB Ltd',ps,es+[S],'Supplemental32 exact models: SCARAs, small/medium arms, hygienic variants and YuMi. Previous36 reviewed models retained. Large/palletizing/paint robots, remaining legacy arms/SWIFTI, AMRs, controllers/software/application cells and other semiconductor/storage products plus final SoftBank disposition remain to research.')]
(out/'batch-0107.json').write_text(json.dumps({'companies':cs},indent=2));print(len(ps))
