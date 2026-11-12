from research_helpers import *
base='https://www.abb.com/global/en/areas/robotics/products/robots/'
ps=[];es=[]
def group(path,rows,kind,axis=None):
 e=ev(base+path,'Current manufacturer available-variants table directly reviewed. Exact variants preserved, reach distinguished from delta workspace diameter. Performance maxima not inferred as simultaneous operating limits.');es.append(e)
 for name,payload,size,extra in rows:
  attrs={'manufacturer_model':name,'robot_type':kind,'rated_payload_kg':payload,**extra}
  if size is not None:attrs['workspace_diameter_m' if kind=='delta' else 'reach_m']=size
  if axis is not None:attrs['axes']=axis
  ps.append(p('ABB '+name,kind.capitalize()+' industrial robot variant.',e,'commercial',roles=['commercial_partner'],typ='product',sector='robotics',sub='industrial_robotics',attributes=attrs))
group('collaborative-robots/powa',[(f'PoWa {n}',n,None,{'wrist_reach_m':w,'flange_reach_m':f}) for n,w,f in [(7,.91,1.05),(10,1.52,1.67),(13,1.34,1.49),(16,1.96,2.10),(20,1.67,1.82),(30,1.35,1.50)]],'collaborative')
group('collaborative-robots/gofa',[('GoFa 5',5,None,{'wrist_reach_m':.95,'flange_reach_m':1.05}),('GoFa 10',10,None,{'wrist_reach_m':1.52,'flange_reach_m':1.62,'wrist_down_max_payload_kg':12}),('GoFa 12',12,None,{'wrist_reach_m':1.27,'flange_reach_m':1.37,'wrist_down_max_payload_kg':14})],'collaborative')
group('articulated-robots/large-robots/irb-8700',[('IRB 8700-800/3.50',800,3.5,{'wrist_down_max_payload_kg':1000}),('IRB 8700-550/4.20',550,4.2,{}),('IRB 8700-800/3.50 with LeanID',800,3.5,{'integrated_dress_pack':'LeanID'}),('IRB 8700-550/4.20 with LeanID',550,4.2,{'integrated_dress_pack':'LeanID'})],'articulated')
group('articulated-robots/medium-robots/irb-2600',[('IRB 2600-20/1.65',20,1.65,{}),('IRB 2600-12/1.65',12,1.65,{}),('IRB 2600-12/1.85',12,1.85,{})],'articulated')
group('articulated-robots/small-robots/irb-1300',[('IRB 1300-11/0.9',11,.9,{}),('IRB 1300-10/1.15',10,1.15,{}),('IRB 1300-7/1.4',7,1.4,{}),('IRB 1300-12/1.4',12,1.4,{})],'articulated')
group('articulated-robots/small-robots/irb-1100',[('IRB 1100-4/0.475',4,.475,{}),('IRB 1100-4/0.58',4,.58,{})],'articulated')
group('articulated-robots/small-robots/irb-1200-next-generation',[('IRB 1200-5/0.9 Gen2',5,.9,{}),('IRB 1200-7/0.7 Gen2',7,.7,{}),('IRB 1200-8/0.9 Gen2',8,.9,{}),('IRB 1200-9/0.7 Gen2',9,.7,{})],'articulated')
group('delta-robots/irb-365',[('IRB 365-1.5/800',1.5,.8,{}),('IRB 365-1.5/1100',1.5,1.1,{}),('IRB 365-1.5/1300',1.5,1.3,{})],'delta',5)
group('delta-robots/irb-360',[('IRB 360-1/1130',1,1.13,{}),('IRB 360-3/1130',3,1.13,{}),('IRB 360-1/1600',1,1.6,{}),('IRB 360-6/1600',6,1.6,{}),('IRB 360-8/1130',8,1.13,{})],'delta')
group('delta-robots/irb-390',[('IRB 390-15/1300',15,1.3,{'axes':4}),('IRB 390-10/1300',10,1.3,{'axes':5})],'delta')
S=ev('https://new.abb.com/news/detail/137499/abb-expands-automation-offering-with-acquisition-of-rotork','July2026 ABB release still describes SoftBank robotics divestment as signed with expected H22026 closing; current closing not established. Parent represented as brand commercial relationship, not unsupported present legal owner.')
for x in ps:x['evidence'].append(S);x['attributes']['company_relationship_scope']='ABB-branded robotics portfolio; commercial parent relationship; SoftBank sale completion not verified'
cs=[company('ABB Ltd',ps,es+[S],'Thirty-six exact current robot variants reviewed including2026 PoWa; wrist/flange reach and wrist-down payload exceptions preserved. Remaining arms/SCARAs/paint robots/AMRs/controllers/software, application cells, semiconductor/battery offerings and latest SoftBank closing status remain to research; no claim portfolio complete.')]
(out/'batch-0106.json').write_text(json.dumps({'companies':cs},indent=2));print(len(ps))
