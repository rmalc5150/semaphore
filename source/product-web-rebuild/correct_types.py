import sys,boto3
sys.path.insert(0,'/home/ec2-user/data-collection-processing')
from company_catalogue_pipeline import connection
c=connection(boto3.Session(region_name='us-east-1'),False)
try:
 with c.cursor() as q:
  q.execute('SET @app_actor=%s,@app_change_reason=%s',('direct-web-product-rebuild/2026-10-20','Refine generic-name aliases and avoid manufacturer roles on developmental technology'))
  q.execute("UPDATE product_aliases SET alias_type='generic_name' WHERE alias IN ('voclosporin','berotralstat','peramivir') AND review_status='pending'")
  q.execute("DELETE pc FROM product_companies pc JOIN products p USING(product_id) WHERE pc.role='manufacturer' AND pc.review_status='pending' AND p.canonical_name IN ('BMS 5.0','KAF electric school bus powertrain','48V monolithic solid-state stack','72V monolithic solid-state stack') AND JSON_UNQUOTE(JSON_EXTRACT(p.attributes,'$.research_method'))='direct_web_browsing'")
 c.commit();print('Refinements committed')
finally:c.rollback();c.close()
