import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from research_helpers import ev,p

company_id='cmp_08fb7be5-e389-4bd5-948b-5fc46ab7b4f6'
source='https://support.xy.company/hc/en-us/articles/360017627794-How-are-XY-and-XYO-related'
store='https://support.xy.company/hc/en-us/articles/360025398013-What-is-the-XYO-Online-Store'
products=[
 p('COIN App','Mobile application and rewards platform that uses the XYO network to let users collect COIN and geomine location data.',source,roles=['developer','owner'],typ='technology',sector='robotics',sub='robotics_software',aliases=['COIN']),
 p('SentinelX','Bluetooth-enabled hardware device used with the COIN app and XYO network for geomining and location data.',store,life='commercial',roles=['developer','owner'],typ='product',sector='robotics',sub='sensing',aliases=['SentinelX']),
 p('BridgeX','Hardware bridge device that connects XYO-enabled devices to the XYO network.',store,life='commercial',roles=['developer','owner'],typ='product',sector='robotics',sub='sensing',aliases=['BridgeX']),
 p('XY4+','Fourth-generation XY Finder Bluetooth item-finder device for locating misplaced belongings.',source,life='commercial',roles=['developer','owner'],typ='product',sector='robotics',sub='sensing',aliases=['XY Finder','XY Findables']),
 p('XYO Network','Decentralized location-oracle network and protocol for recording and verifying data from physical-world devices.',source,life='commercial',roles=['developer','owner'],typ='technology',sector='robotics',sub='robotics_software',aliases=['XYO']),
]
manifest={'batch_id':'batch-0441','companies':[{'company_id':company_id,'products':products,'evidence':[ev(source,'XY Labs support article describes the company product lines and XYO relationship.'),ev(store,'XY Labs support article identifies SentinelX and BridgeX as products sold through the XYO store.')],'status':'partial','coverage_note':'Official XY Labs support pages identify the current COIN, SentinelX, BridgeX, XY4+/XY Finder, and XYO Network product lines; XY Find It is documented as retired and excluded.'}]}
import json
from pathlib import Path
Path('/home/ec2-user/product-web-rebuild/batch-0441.json').write_text(json.dumps(manifest,indent=2))
print('/home/ec2-user/product-web-rebuild/batch-0441.json')
