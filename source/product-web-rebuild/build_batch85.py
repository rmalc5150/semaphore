from research_helpers import *
b='https://www.kuka.com/en-us/products/robotics-systems/industrial-robots/'
es=[];ps=[]
def group(slug,desc,rows,axes):
 s=ev(b+slug,'Manufacturer current exact model table reviewed. Zero placeholder specifications omitted; distinct variants preserved.')
 es.append(s)
 for n,load,reach,env in rows:
  a={'axes':axes,'version_environment':env}
  if load:a['payload_kg_as_listed']=load
  if reach:a['reach_mm_as_listed']=reach
  ps.append(p('KUKA '+n,desc,s,'commercial',roles=['developer'],typ='product',sector='robotics',sub='industrial_robotics',attributes=a))
group('kr-4-agilus','Compact industrial robot.',[('KR 4 R600',4,601,'Standard')],6)
group('lbr-iisy-cobot','Collaborative industrial robot.',[('LBR iisy 3 R760',3,760,'Standard'),('LBR iisy 6 R1300',6,1300,'Standard'),('LBR iisy 8 R930',8,930,'Standard'),('LBR iisy 11 R1300',11,1300,'Standard'),('LBR iisy 11 R1300 CR',11,1300,'Cleanroom'),('LBR iisy 15 R930',15,930,'Standard'),('LBR iisy 15 R930 CR',15,930,'Cleanroom')],6)
# Delta website's field called reach conflicts with workspace diameters in model names; omit ambiguous geometry rather than misinterpret it.
group('kr-delta-roboter','Delta handling robot.',[(n,w,None,e) for n,w,e in [('KR 3 D1200',6,'Standard'),('KR 3 D1200 HM',6,'Hygienic Machine'),('KR 15 D1200-2',15,'Standard'),('KR 15 D1600-2',15,'Standard')]],4)
rows=[('KR 6 R500 Z200-2',6,500,'Standard'),('KR 6 R700 Z170 HO',6,700,'Food'),('KR 6 R700 Z200-2',6,700,'Standard')]
for reach,z,env in [(650,340,'Cleanroom'),(650,400,'Standard'),(750,340,'Cleanroom'),(750,400,'Standard'),(750,600,'Standard'),(850,340,'Cleanroom'),(850,400,'Standard')]:rows.append((f'KR 12 R{reach} Z{z}'+(' CR' if env=='Cleanroom' else ''),12,reach,env))
rows.append(('KR 13 R850 Z340 HO',13,850,'Food'))
for reach in [1000,1200,800]:
 for z,env in [(390,'Cleanroom'),(450,'Standard')]:rows.append((f'KR 20 R{reach} Z{z}'+(' CR' if env=='Cleanroom' else ''),20,reach,env))
rows.append(('KR 60 R1200 Z400',60,1200,'Standard'))
group('kr-scara-robot','SCARA assembly robot.',rows,4)
cs=[company('Kuka AG ADR',ps,es,'30 exact models from KR4AGILUS, LBRiisy, KRDELTA and KRSCARA technical tables reviewed. KR40R1000Z500 zero-spec/no-datasheet placeholder deferred. Delta reach/workspace ambiguity not silently converted. Other robot families, mobile robots, controllers, software, periphery, Swisslog and system offerings remain to research; family-only umbrella duplicates avoided.')]
(out/'batch-0085.json').write_text(json.dumps({'companies':cs},indent=2));print(len(ps))
