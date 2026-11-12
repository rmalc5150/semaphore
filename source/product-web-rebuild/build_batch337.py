from research_helpers import *
from catalogue_table_parser import Table
rows=[('AcDcConverter','Off-line power converter IC.',74),('PFCIC','Power-factor-correction IC.',1),('DcDcConverter','DC/DC converter IC.',14),('LinearRegulator','Linear regulator IC.',11),('GateDriverIC','Gate-driver IC.',2),('LedDriver','LED driver IC.',7),('A_HeadLightIc','Automotive headlight driver IC.',3),('2Ph_StepMotorUnp','Unipolar two-phase stepper-motor driver.',6),('A_DcBrushMotor','Automotive motor-driver IC.',2),('A_DiscreteModule','Automotive discrete power module.',4),('Array','Semiconductor transistor array.',49)]
products=[];evidence=[];review=[]
for slug,desc,expected in rows:
 src=ev('https://www.semicon.sanken-ele.co.jp/ctrl/en/product/category/'+slug+'/','Public website catalogue table manually reviewed: exact part numbers, manufacturer status, automotive qualification and packages. Multirow headings excluded.')
 evidence.append(src);t=Table();t.feed((out/('sanken-'+slug+'-table.html')).read_text().split('|split_content|')[0]);rr=[r for r in t.rows if len(r)>3 and r[1] in ['ACTIVE','PREVIEW','NRND','DISCONTINUED']];assert len(rr)==expected,(slug,len(rr))
 for r in rr:
  name=r[-1];assert name not in [p['canonical_name'] for p in products]
  products.append(p(name,desc,src,life={'ACTIVE':'commercial','PREVIEW':'development','NRND':'unknown','DISCONTINUED':'discontinued'}[r[1]],typ='product',sector='semiconductors',sub='chip_design',roles=['developer','manufacturer'],attributes={'manufacturer_status':r[1],'automotive_qualified':r[2],'package':r[3]}))
  review.append({'category':slug,'name':name,'status':r[1],'automotive_qualified':r[2],'package':r[3]})
co=dict(company_id='cmp_283cd328-5e4b-448f-9b81-0d640e25abca',products=products,evidence=evidence,status='partial',coverage_note='173 exact part numbers from eleven further fully reviewed catalogue tables; 233 identities across fourteen categories recorded. Four converter previews remain development. Table subheadings excluded. Partial: discrete transistors/diodes, LEDs, MCU standalone offerings and NRND/discontinued inventory remain. Package suffixes retained as distinct exact catalogue parts; no guessed specifications.')
(out/'sanken-ic-reviewed-20261021.json').write_text(json.dumps(review,indent=2))
(out/'batch-0337.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
