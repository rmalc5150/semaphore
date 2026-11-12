from research_helpers import *
import re
A=ev('https://www.keyence.com/products/vision/vision-sys/vs/models/','Directly reviewed public model list served by this manufacturer page:79 entries including26 smart cameras,2 Ethernet cameras,7 lighting/controller components and1 AI addin licence selected; generic cables/brackets not indiscriminately classified.')
S=ev('https://www.keyence.com/products/vision/vision-sys/industries/semiconductor-manufacturing-electronics/','Manufacturer explicitly applies VS systems to semiconductor wafer seating/notch/rack inspection; semiconductor equipment classification is not based solely on generic electronics use.')
ps=[]
for m in json.loads((out/'keyence-vs-public-models.json').read_text())['models']:
 if m['productTypeName'] not in ['Controller/Head','Camera','Illumination/Illumination controller'] and m['webProductName']!='VS-AD1':continue
 code=m['webProductName'];label=m['salesProductName'];e=ev('https://www.keyence.com'+m['overviewUrl'],'Exact public catalogue model identity, component category and manufacturer discontinuedFlag reviewed.')
 attrs={'manufacturer_part_number':code,'catalogue_component_type':m['productTypeName'],'manufacturer_discontinued_flag':m['discontinuedFlag'],'evidence_method':'review of public website catalogue model data'}
 mp=re.search(r'(\d+(?:\.\d+)?)\s*(?:M pixel|Megapixel)',label,re.I)
 if mp:attrs['resolution_megapixels']=float(mp.group(1))
 if 'Monochrome' in label or 'monochrome' in label:attrs['image_type']='monochrome'
 elif 'Color' in label or '(color)' in label:attrs['image_type']='color'
 if 'C-mount' in label:attrs['lens_mount']='C-mount'
 if 'Short range' in label:attrs['working_range_type']='short-range zoom'
 elif 'Standard range' in label:attrs['working_range_type']='standard-range zoom'
 desc='Machine-vision smart camera for industrial inspection.' if m['productTypeName']=='Controller/Head' else 'Ethernet-connected zoom camera for machine vision.' if m['productTypeName']=='Camera' else 'Machine-vision illumination or lighting-control component.'
 if code=='VS-AD1':desc='AI add-in software licence for VS machine vision.'
 ps.append(p('KEYENCE '+code,desc,e,'discontinued' if m['discontinuedFlag'] else 'commercial',roles=['developer'],typ='technology' if code=='VS-AD1' else 'product',sector='semiconductors',sub='semiconductor_equipment',attributes=attrs,evidence=[e,A,S]))
B=ev('https://www.keyence.com/products/microscope/fluorescence-microscope/bz-x1000/models/bz-x1100/','Current BZX1100 microscope specification and ten exact imaging/analysis module codes; 10MP native sensor vs interpolated40MP output distinguished.')
ps.append(p('KEYENCE BZ-X1100','Automated inverted fluorescence microscope head for biological imaging.',B,'commercial',roles=['developer'],typ='product',sub='research_tools',attributes={'native_sensor_megapixels':10,'maximum_interpolated_output_megapixels':40,'observation_modes':['brightfield','fluorescence','phase contrast','oblique illumination'],'fluorescence_channels_max':11,'xy_stage_travel_mm':[114,80],'z_stage_travel_mm':8}))
for code,desc in [('BZ-H5XF','Optical-sectioning imaging module.'),('BZ-H5XJ','Stitching and multipoint imaging module.'),('BZ-H5XZ','Z-stack acquisition module.'),('BZ-H5XI','Image-cytometer acquisition and analysis module.'),('BZ-H5XT','Time-lapse imaging and measurement module.'),('BZ-H5A','Microscope-image analysis application.'),('BZ-H5M','Image dimension, area and brightness measurement application.'),('BZ-H5R','Three-dimensional image analysis application.'),('BZ-H5K','Motion-tracking and time-series image analysis application.'),('BZ-H5C','Hybrid cell-counting image analysis software.')]:
 attrs={'manufacturer_part_number':code,'compatible_platform':'BZ-X1100/BZ-X1000'}
 if code=='BZ-H5XI':attrs['acquisition_dependencies']=['BZ-H5XZ','BZ-H5XJ'];attrs['analysis_dependency']='BZ-H5C'
 ps.append(p('KEYENCE '+code,desc,B,'commercial',roles=['developer'],typ='technology',sub='research_tools',attributes=attrs))
C=ev('https://www.keyence.com/products/microscope/colony-counter/bc-1000/models/bc-1000/','Current BC1000 biological colony-counting instrument; exact20MP sensor and105mm measurement area.')
ps.append(p('KEYENCE BC-1000','Automated microbiological colony-counting instrument.',C,'commercial',roles=['developer'],typ='product',sub='research_tools',attributes={'sensor_megapixels':20,'measurement_area_diameter_mm':105,'supported_samples':['Petri dishes','well plates','culture film']}))
D=ev('https://www.keyence.com/products/microscope/fluorescence-microscope/bz-x700/models/bz-x810/','Manufacturer explicitly marks BZX810 discontinued and recommends BZX1100; current supplier status not inferred from older articles.')
ps.append(p('KEYENCE BZ-X810','Discontinued automated inverted fluorescence microscope.',D,'discontinued',roles=['developer'],typ='product',sub='research_tools',attributes={'manufacturer_recommended_replacement':'BZ-X1100'}))
cs=[company('Keyence Corporation',ps,[A,S,B,C,D],'Forty-nine exact current/discontinued product identities reviewed:36 VS inspection components/software plus13 microscopy/colony-analysis products. Native sensor resolution not conflated with interpolated output. Generic cables/brackets deferred, public model data reviewed manually before import. Complete3D/2D robot-vision/CVX/XG/VK/VHX/metrology portfolios, remaining microscope options and legacy products still to research.')]
(out/'batch-0111.json').write_text(json.dumps({'companies':cs},indent=2));print(len(ps))
