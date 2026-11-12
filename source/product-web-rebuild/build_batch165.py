from research_helpers import *
base='https://www.himax.com.tw/products/'
products=[];sources=[]
def add(code,desc,path,aliases=[],roles=['developer'],attrs={}):
 e=ev(base+path,'Himax primary product page confirms named part or module and described function. Current production and ordering availability unverified. Component chips, assembled modules and development boards kept distinct.')
 sources.append(e)
 products.append(p('Himax '+code,desc,e,typ='product',sector='semiconductors',sub='chip_design',aliases=[code]+aliases,roles=roles,attributes={'current_availability':'unverified',**attrs}))
add('HM8030','Eight-megapixel CMOS image sensor with dual-lane MIPI CSI-2 output.','cmos-image-sensor/image-sensors/hm8030/',attrs={'package_part_number':'HM8030-AGA','active_resolution':'3280x2464','frame_rate_full_resolution_fps':15})
for code,res in [('HM01B0','320x320'),('HM0360','640x480'),('HM0361','640x480'),('HM11B1','1280x800')]:
 add(code,'Always-on CMOS image sensor.','cmos-image-sensor/always-on-vision-sensors/',attrs={'resolution':res})
add('HX6538','WiseEye2 endpoint AI microcontroller integrating Arm Cortex-M55 and Ethos-U55.','wiseeye-ai-sensing/wiseeye2-ai-processor/',aliases=['WiseEye2 AI processor'],attrs={'module_table_package_part_number':'HX6538-A06TDFG'})
add('HX6537','WiseEye1 AI processor; exact chip code confirmed by manufacturer module table.','wiseeye-ai-sensing/wiseeye-solutions/',aliases=['WiseEye1 AI processor'])
for code in ['ISM01Q-03M0098','ISM01Q-03M0198','ISM01Q-03M00F9','ISM01Q-03M01F9','ISM028-03M0098','ISM028-03M0198']:
 add(code,'Endpoint AI camera module integrating processor, image sensor and lens.','wiseeye-ai-sensing/wiseeye-solutions/',attrs={'processor':'HX6537' if code.startswith('ISM01Q') else 'HX6538','sensor_package':'HM0360-MWB','assembly_scope':'camera_module_not_standalone_processor'})
add('first-generation WiseEye Module','Earlier compact module combining WE1 processor and HM01B0 sensor; exact ordering code unverified.','wiseeye-ai-sensing/wiseeye-solutions/',attrs={'dimensions_mm':[12.5,17.0,2.45],'ordering_code':'unverified'})
add('WE1 Plus Endpoint AI Development Board','40x27 mm development board integrating camera, microphones and accelerometer; manufacturer links SparkFun item 17256.','wiseeye-ai-sensing/wiseeye-development-platform/',aliases=['WE1 Plus EVB'],attrs={'retailer_item_reference':'SparkFun 17256','assembly_scope':'development_board'})
for code,desc,path,aliases in [
 ('HX7322','Color-sequential LCoS microdisplay supporting 1920x1080 output.','color-sequential-lcos/hx7322/',[]),
 ('HX7318','Color-sequential LCoS microdisplay supporting 1366x768 output.','color-sequential-lcos/hx7318/',[]),
 ('HX7819-A','LCoS controller with four-lane MIPI input supporting HX7322 and HX7318 panels.','controller-ic/hx7819/',['HX7819']),
 ('HX8852-A','MIPI-compatible LCoS video controller supporting output up to 640x480 at 120 Hz.','controller-ic/hx8852/',['HX8852']),
 ('HX7028FL','Front-lit LCoS display module supporting 1280x720. Conflicting native-resolution numbers on manufacturer page withheld.','front-lit-lcos/hx7028fl/',[])]:
 add(code,desc,'microdisplay-products/'+path,aliases)
add('LQ001','Three-channel liquid-crystal lens driver listed under Liqxtal subsidiary catalogue.','liqxtal-technology/lc-lens-driver/',roles=['commercial_partner'],attrs={'operating_input_voltage_v':[2.5,3.3],'maximum_output_voltage_v':15,'corporate_scope':'parent catalogue listing; direct development ownership not inferred'})
co=company('Himax Technologies, Inc.',products,list({e['reference']:e for e in sources}.values()),'Added Always-On sensors, HM8030, WiseEye1/HX6537 and WiseEye2/HX6538 processors, six individually coded camera modules, earlier HM01B0 module, WE1 Plus development board, five microdisplay/controller parts and Liqxtal lens driver. Earlier display/analogue/LED tables already entered. Need WLO/diffuser catalogue, legacy microdisplay models, current announcements, additional development kits, package variants, family-to-variant relationships and production availability. Conflicting HX7028FL native resolution withheld. Scan remains partial.')
(out/'batch-0165.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
