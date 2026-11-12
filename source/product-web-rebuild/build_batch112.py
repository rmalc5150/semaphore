from research_helpers import *
cid=next(c['company_id'] for c in cohort if c['canonical_name']=='Keyence Corporation')
seen={p0['canonical_name'] for f in out.glob('batch-*.receipt.json') for c in json.loads(f.read_text())['manifest']['companies'] if c['company_id']==cid for p0 in c['products']}
R=ev('https://www.keyence.com/products/vision/vision-sys/3d_vgr/','Manufacturer identifies3D guided robot bin-picking/assembly/machine-tending solution; four-camera/projector sensing architecture not four separate invented camera SKUs.')
V=ev('https://www.keyence.com/products/microscope/laser-microscope/applications/3d-measurement-applications-of-integrated-circuits-ics.jsp','Manufacturer directly applies VKX4000 family to IC/BGA/wirebond/contact-probe inspection, supporting semiconductor-equipment classification.')
ps=[];es=[]
for key in ['3d-vgr','bz-x1000','vk-x4000']:
 data=json.loads((out/('keyence-'+key+'-public-models.json')).read_text());e=ev(data['page'],'Public manufacturer website model-list data directly reviewed, exact names/types/descriptions and discontinued flags; only reviewed identities selected.');es.append(e)
 for m in data['data']['models']:
  code=m['webProductName'];name='KEYENCE '+code
  if name in seen:continue
  if key=='3d-vgr' and code not in ['CV-X482D','RB-1200','RB-500','RB-800','CA-E200T','OP-88216','OP-88217','OP-88218','OP-88867','OP-88868']:continue
  attrs={'manufacturer_part_number':code,'catalogue_component_type':m['productTypeName'],'manufacturer_discontinued_flag':m['discontinuedFlag']}
  src=ev('https://www.keyence.com'+m['overviewUrl'],'Exact manufacturer catalogue model and functional description reviewed.'); evidence=[src,e]
  typ='product';sector='biotech';sub='research_tools'
  if key=='3d-vgr':
   sector='robotics';sub='autonomy_and_components';evidence.append(R)
   desc={'CV-X482D':'Controller for3D robot vision.','RB-1200':'Three-dimensional robot-vision camera.','RB-500':'Three-dimensional robot-vision camera.','RB-800':'Three-dimensional robot-vision camera.','CA-E200T':'Input unit for3D robot-vision cameras.','OP-88216':'Calibration target for RB500 robot vision.','OP-88217':'Calibration target for RB800/1200 robot vision.','OP-88218':'Robot-vision calibration target.','OP-88867':'Optical filter set for RB500/800 robot vision.','OP-88868':'Optical filter set for RB1200 robot vision.'}[code]
  elif key=='bz-x1000':
   desc={'BZ-X1000':'Controller for automated fluorescence microscopy.','BZ-XLC1':'Confocal laser-scanning microscopy unit.','BZ-H5CM':'Macro cell-counting image-analysis application.','BZ-H5XL':'Confocal image-acquisition software module.','BZ-A1W':'Standard microscope configuration kit; contents not independently reconciled.','BZ-L1':'Confocal microscope configuration kit; contents not independently reconciled.'}.get(code,'Dedicated biological-microscopy sample holder, optical filter or accessory.')
   if code.startswith('BZ-H'):typ='technology'
   if code.startswith('OP-'):attrs['manufacturer_function']=m['salesProductName']
   if code in ['BZ-A1W','BZ-L1']:attrs['offering_scope']='manufacturer-listed kit; exact contents unverified'
  else:
   sector='semiconductors';sub='semiconductor_equipment';evidence.append(V)
   desc='Dedicated optical-metrology instrument component for semiconductor inspection.'
   attrs['manufacturer_function']=m['salesProductName']
   if code in ['VK-A4','VK-H4CA','VK-H4I','VK-H4J']:typ='technology';desc='Optical-metrology analysis or acquisition software for semiconductor inspection.'
   if code in ['VK-B3B','VK-B3C','VK-B3H','VK-B3M','OP-89282','VK-GP3']:attrs['stage_diameter_mm']=300
  ps.append(p(name,desc,src,'discontinued' if m['discontinuedFlag'] else 'commercial',typ=typ,sector=sector,sub=sub,attributes=attrs,evidence=evidence))
cs=[company('Keyence Corporation',ps,es+[R,V],'Supplemental56 exact microscope modules/accessories,3D guided-robot vision and VKX4000 metrology components reviewed;49 previous records retained. BZX1000 is a controller, BZX1100 the separate head, with confocal and count modules distinct. Two kit identities lack full contents. Generic camera/power cables deferred; remaining full vision/metrology/legacy portfolio and detailed per-model specifications require further research.')]
(out/'batch-0112.json').write_text(json.dumps({'companies':cs},indent=2));print(len(ps))
