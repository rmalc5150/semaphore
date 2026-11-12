from research_helpers import *
base='https://shop.amplitechinc.com/'
data=json.loads((out/'amplitech-products.json').read_text())['products']
groups=[('lna-s','Low-noise amplifier MMIC',['AGLNA180405','AGLNA035082','AGLNA160410','AGLNA020150','AGLNA013048Q','AGLNA008020','AGLNA014222','AGLNA014221','AGLNA160420','AGLNA145245','AGLNA018047','AGLNA013048']),('mpa-s','Medium-power amplifier MMIC',['AGMPA080160','AGMPA172212','AGMPA171228','AGMPA086135','AGMPA078161','AGMPA165215B','AGMPA165215']),('band-pass-filters','Bandpass filter IPD MMIC',['AGBPF100','AGBPF063','AGBPF295','AGBPF150','AGBPF118','AGBPF078','AGBPF069','AGBPF022','AGBPF263','AGBPF195']),('attenuators','Attenuator MMIC',['AGATN00','AGATN02','AGATN03','AGATN06','AGATN10']),('low-pass-filters','Low-pass filter MMIC',['AGLPF100','AGLPF080','AGLPF040']),('band-stops','Band-stop filter MMIC',['AGBSF295']),('termination','RF termination MMIC',['AGTRM050']),('rf-transitions','RF transition MMIC',['AGN001-CAL','AGN-001']),('rf-couplers','RF coupler MMIC',['AGN002-5'])]
ps=[];es=[]
for handle,desc,names in groups:
 src=ev(base+'collections/'+handle,'Reviewed manufacturer MMIC category table; exact part identities checked against public storefront catalogue. Catalogue listing establishes offered product, not unit sales.')
 es.append(src)
 for n in names:
  item=next(x for x in data if x['title']==n)
  ps.append(p('AmpliTech '+n,desc+'.',src,'commercial',roles=['developer'],typ='product',sector='semiconductors',sub='chip_design',attributes={'manufacturer_part_number':n,'brand':'AGMDC/AmpliTech','official_product_url':base+'products/'+item['handle']}))
cs=[company('Amplitech Group Inc',ps,es,'42 exact MMIC entries reviewed across nine populated storefront categories; RF calibration and thru-line categories empty. Passive mechanical couplers/dividers, waveguide adapters, radio systems and bench instruments not automatically classified as chips. Spectrum distributed package/lid identities and further semiconductor-relevant catalogue/specification detail remain to research.')]
(out/'batch-0081.json').write_text(json.dumps({'companies':cs},indent=2));print(len(ps))
