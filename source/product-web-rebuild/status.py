import sys,json,boto3
sys.path.insert(0,'/home/ec2-user/data-collection-processing')
from company_catalogue_pipeline import connection
c=connection(boto3.Session(region_name='us-east-1'),False)
try:
 with c.cursor() as q:
  for sql in ["SELECT COUNT(*) products FROM products","SELECT last_product_scan_status,COUNT(*) n FROM companies WHERE review_status='verified' AND collection_enabled=1 AND archived_at IS NULL GROUP BY last_product_scan_status","SELECT COUNT(*) bad_method FROM products WHERE JSON_UNQUOTE(JSON_EXTRACT(attributes,'$.research_method'))<>'direct_web_browsing' OR JSON_EXTRACT(attributes,'$.research_method') IS NULL","SELECT COUNT(*) unsupported_associations FROM product_companies pc JOIN companies c USING(company_id) WHERE c.review_status<>'verified' OR c.collection_enabled<>1 OR c.archived_at IS NOT NULL"]:
   q.execute(sql);print(json.dumps(q.fetchall(),default=str))
finally:c.rollback();c.close()
