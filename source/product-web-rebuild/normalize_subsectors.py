import sys,json,boto3
from pathlib import Path
sys.path.insert(0,'/home/ec2-user/data-collection-processing')
from company_catalogue_pipeline import connection
from product_web_registry import normalize_subsector,ACTOR
c=connection(boto3.Session(region_name='us-east-1'),False)
changes=[]
try:
 with c.cursor() as q:
  q.execute("SELECT GET_LOCK('optima_product_catalogue_v1',0) acquired");assert q.fetchone()['acquired']==1
  q.execute('SET @app_actor=%s,@app_change_reason=%s',(ACTOR,'Align researched product subsectors to config/sectors.v1.json; retain detailed research category in attributes'))
  q.execute('SELECT product_id,sector_id,subsector_id,attributes FROM products')
  for row in q.fetchall():
   original=row['subsector_id'];item={'sector_id':row['sector_id'],'subsector_id':original,'attributes':json.loads(row['attributes'])}
   normalize_subsector(item)
   if item['subsector_id']!=original:
    assert item['attributes']['research_batch']==ACTOR
    q.execute('UPDATE products SET subsector_id=%s,attributes=%s WHERE product_id=%s',(item['subsector_id'],json.dumps(item['attributes']),row['product_id']))
    changes.append({'product_id':row['product_id'],'before':original,'after':item['subsector_id']})
 c.commit();Path('/home/ec2-user/product-web-rebuild/subsector-normalization.json').write_text(json.dumps(changes,indent=2));print(json.dumps({'normalized_products':len(changes)}))
except Exception:
 if c.open:c.rollback()
 raise
finally:c.close()
