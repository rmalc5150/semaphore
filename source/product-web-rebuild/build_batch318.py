from research_helpers import *
rows=json.loads((out/'cirrus-reviewed-20261021.json').read_text())
evs={cat:ev('https://www.cirrus.com/product-category/'+cat,'Reviewed active product-table entries; resource-library references alone not treated as current products.') for cat in ['amplifiers','codecs','d-a-converters','a-d-converters']}
products=[]
for r in rows:
 cat=r['category'];f=r['fields'];attrs={'published_package':r['package'],'published_status':f[1]}
 if cat=='amplifiers':desc='Mono smart audio-amplifier integrated circuit.'
 elif cat=='codecs':
  desc='Audio codec and mixed-signal interface integrated circuit.';attrs.update(channels_in=f[4],channels_out=f[5])
 elif cat=='d-a-converters':
  desc='Audio digital-to-analog converter integrated circuit.';attrs.update(channels_out=f[3],resolution_bits=f[7],sample_rate_khz=f[6])
 else:
  desc='Audio analog-to-digital converter integrated circuit.';attrs.update(channels_in=f[3],resolution_bits=f[7],sample_rate_khz=f[6])
 products.append(p(r['name'],desc,evs[cat],'commercial',roles=['developer'],sector='semiconductors',sub='chip_design',typ='product',attributes=attrs))
a=ev('https://www.cirrus.com/product-category/timing','Three active current timing IC entries; old datasheet references not automatically current.')
for n in ['CS2500','CS2501','CS2600']:products.append(p(n,'Fractional-N clock generation/multiplication integrated circuit.',a,'commercial',sector='semiconductors',sub='chip_design',typ='product'))
b=ev('https://www.cirrus.com/news/2026/industrial-imaging-high-precision-scanning','Three named industrial imaging ICs available for sampling April 2026, not assumed mass production.')
for n,ch in [('CS82L41',1),('CS82L44',4),('CS82L46',6)]:products.append(p(n,'Imaging analog-front-end integrated circuit.',b,'development',sector='semiconductors',sub='chip_design',typ='product',attributes={'channels':ch,'published_release_status':'sampling'}))
c=ev('https://www.cirrus.com/news/2025/closed-loop-haptic-drivers-for-automotive','Three named automotive haptic-driver variants; availability status retained cautiously.')
for n in ['CS40L51','CS40L52','CS40L53']:products.append(p(n,'Automotive closed-loop haptic-driver integrated circuit.',c,'unknown',sector='semiconductors',sub='chip_design',typ='product'))
co=dict(company_id='cmp_28b4b76e-bae7-4e15-9389-9fb7686b3d4d',products=products,evidence=list(evs.values())+[a,b,c],status='partial',coverage_note='Thirty-seven exact chip identities. Partial: current page renders fewer rows than search index totals, other new converters, legacy/EOL devices, haptics/power and signal processing portfolio remain. Resource documents not blindly treated as active sales. Package/ordering suffixes grouped under chip identity. New imaging chips explicitly sampling, not commercial mass-production assertion. Published malformed codec rate ranges not copied.')
(out/'batch-0318.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
