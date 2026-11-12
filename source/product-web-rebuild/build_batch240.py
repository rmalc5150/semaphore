from research_helpers import *
a=ev('https://www.qualcomm.com/smartphones/product-list','First public results page reviewed; total catalogue reports 98 entries, but only visible entries used here.')
b=ev('https://www.qualcomm.com/smartphones/products','Public comparison table explicitly labels selected platforms Active. Active is not a guarantee of stock or geography.')
visible=['8 Elite Gen 6','8 Elite Extreme Gen 6','4 Gen 5','6 Gen 5','6 Gen 3','4 Gen 4','6s 4G Gen 2','8 Gen 5','6s Gen 4','8 Elite Gen 5','7s Gen 4','6 Gen 4']
active=['8 Gen 5','8 Elite Gen 5','8s Gen 4','8 Elite','8s Gen 3','8 Gen 3','8 Gen 2','888+ 5G','888 5G','865 5G','865+ 5G','8 Gen 1','8+ Gen 1','7+ Gen 3','7s Gen 2','782G','768G 5G','7 Gen 1','6 Gen 3','6s Gen 4','6 Gen 4','6s 4G Gen 1','6s Gen 3','685 4G','690 5G','6 Gen 1','662','680 4G','695 5G','4 Gen 2','4s Gen 2','4 Gen 1']
products=[]
for code in dict.fromkeys(visible+active):
 source=b if code in active else a
 products.append(p('Snapdragon '+code,'Mobile SoC.',source,'commercial' if code in active else 'unknown',roles=['commercial_partner'],typ='product',sector='semiconductors',sub='chip_design'))
co=dict(company_id='cmp_0e22268b-101d-4c31-b347-4b5643dc2949',products=products,evidence=[a,b],status='partial',coverage_note='Named mobile semiconductor platforms recorded under parent Qualcomm Incorporated through subsidiary Qualcomm Technologies; parent relationship commercial_partner, not fabrication attribution. Current comparison-table Active entries commercial; newly visible catalogue entries unknown pending launch/shipment checks. Partial: remaining mobile pages/legacy products, PC, connectivity, RF, automotive, industrial/robotics and licensing portfolios need review. OEM customer phones are not Qualcomm products; integrated GPU/modem feature mentions not automatically separate records.')
(out/'batch-0240.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
