from research_helpers import *
from html.parser import HTMLParser
class Table(HTMLParser):
 def __init__(self):super().__init__();self.rows=[];self.row=None;self.cell=None
 def handle_starttag(self,t,a):
  if t=='tr':self.row=[]
  if t in ['td','th']:self.cell=[]
 def handle_data(self,d):
  if self.cell is not None:self.cell.append(d)
 def handle_endtag(self,t):
  if t in ['td','th'] and self.cell is not None:
   if self.row is not None:self.row.append(' '.join(' '.join(self.cell).split()))
   self.cell=None
  if t=='tr' and self.row is not None:self.rows.append(self.row);self.row=None
products=[];evidence=[];review=[]
for slug,desc,expected in [('digital','Digital power-supply control IC.',4),('A_3Ph_HVBLDCMotor','Automotive intelligent power module.',8),('3Ph_HVBLDCMotor','Intelligent motor-driver power module.',48)]:
 url='https://www.semicon.sanken-ele.co.jp/ctrl/en/product/category/'+('D_PowerManagement' if slug=='digital' else slug)+'/'
 src=ev(url,'Public dynamic catalogue table retrieved using same public request as webpage and manually reviewed. ACTIVE versus PREVIEW preserved; stock badge not used as lifecycle status.')
 evidence.append(src);t=Table();t.feed((out/('sanken-'+slug+'-table.html')).read_text().split('|split_content|')[0])
 rows=t.rows[1:];assert len(rows)==expected,(slug,len(rows))
 for row in rows:
  name=row[-1];status=row[1];assert status in ['ACTIVE','PREVIEW'];assert name not in [x['canonical_name'] for x in products]
  attrs={'manufacturer_status':status,'package':row[3]}
  if slug=='digital':attrs['built_in_mcu']=row[4]
  else:
   ix=4 if slug.startswith('A_') else 5
   attrs.update(breakdown_voltage_v=row[ix],output_current_a=row[ix+1],automotive_qualified=row[2])
  products.append(p(name,desc,src,life='commercial' if status=='ACTIVE' else 'development',typ='product',sector='semiconductors',sub='chip_design',roles=['developer','manufacturer'],attributes=attrs))
  review.append({'category':slug,'name':name,'row':row})
co=dict(company_id='cmp_283cd328-5e4b-448f-9b81-0d640e25abca',products=products,evidence=evidence,status='partial',coverage_note='Sixty exact part numbers from three fully reviewed public catalogue tables: 4 digital control ICs, 8 automotive IPMs, 48 general IPMs. ACTIVE maps commercial and PREVIEW development; no mass-production assumption for previews. Partial: off-line/PFC/DC-DC/LDO/gate/LED/headlight ICs, other motor drivers, discrete modules, arrays, transistors, diodes, LEDs, and NRND/discontinued inventory remain. No customer equipment or wholly separate Allegro catalogue attributed to Sanken.')
(out/'sanken-reviewed-20261021.json').write_text(json.dumps(review,indent=2))
(out/'batch-0336.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
