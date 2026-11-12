import sys,boto3
sys.path.insert(0,'/home/ec2-user/data-collection-processing')
from company_catalogue_pipeline import connection
c=connection(boto3.Session(region_name='us-east-1'),False)
try:
 with c.cursor() as q:
  q.execute('SET @app_actor=%s,@app_change_reason=%s',('product-catalogue-v1','Correct manufactured-for/distributed-by evidence: distribution does not establish manufacture'))
  q.execute("UPDATE product_companies pc JOIN products p USING(product_id) SET pc.role='commercial_partner' WHERE pc.company_id=%s AND p.canonical_name=%s AND pc.role='manufacturer' AND pc.review_status='pending'",('cmp_003129dc-88eb-4cdf-ba03-0dbe194906c9','AVMAPKI FAKZYNJA CO-PACK'))
  print('corrected_distribution_relationships',q.rowcount)
 c.commit()
finally:c.rollback();c.close()
