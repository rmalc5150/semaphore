import sys,json
from pathlib import Path
sys.path.insert(0,'/home/ec2-user/data-collection-processing')
import boto3
from company_catalogue_pipeline import connection
old='https://www.macom.com/products/optical/lasers/25g-fabry-perot-lasers';new='https://www.macom.com/products/optical/lasers/25g_fabry_perot_lasers'
p=Path('/home/ec2-user/product-web-rebuild');r=json.loads((p/'batch-0386.receipt.json').read_text());co=r['manifest']['companies'][0];pid=next(x['inserted_product_id'] for x in co['products'] if x['canonical_name']=='MACOM MAOD-131F25IL1T0')
c=connection(boto3.Session(region_name='us-east-1'),False)
try:
 with c.cursor() as q:
  q.execute('SELECT company_id FROM companies WHERE company_id=%s FOR UPDATE',(co['company_id'],));assert q.fetchone()
  for table,col,where,args in [('products','evidence','product_id=%s',(pid,)),('product_companies','evidence','product_id=%s AND company_id=%s',(pid,co['company_id'])),('companies','last_product_scan_evidence','company_id=%s',(co['company_id'],))]:
   q.execute(f'UPDATE {table} SET {col}=REPLACE(CAST({col} AS CHAR),%s,%s) WHERE {where}',(old,new,*args))
 c.commit()
finally:c.close()
for name in ['batch-0386.json','batch-0386.receipt.json']:
 f=p/name;f.write_text(f.read_text().replace(old,new))
f=p/'build_batch386.py';f.write_text(f.read_text().replace('lasers/25g-fabry-perot-lasers','lasers/25g_fabry_perot_lasers'))
print('Corrected Fabry-Perot source URL in product, company link, scan evidence and batch artifacts.')
