import sys,json,boto3
from pathlib import Path
sys.path.insert(0,'/home/ec2-user/data-collection-processing')
from company_catalogue_pipeline import connection
receipts=list(Path('/home/ec2-user/product-web-rebuild').glob('batch-*.receipt.json'));ids=sorted({c['company_id'] for f in receipts for c in json.loads(f.read_text())['manifest']['companies']})
c=connection(boto3.Session(region_name='us-east-1'),False)
try:
 with c.cursor() as q:
  q.execute('SET SESSION max_execution_time=10000')
  for sql,args in [("SELECT COUNT(*) n,SUM(collection_enabled<>0) unexpectedly_enabled,SUM(JSON_UNQUOTE(JSON_EXTRACT(attributes,'$.research_method'))<>'direct_web_browsing') wrong_method FROM products",()),("SELECT company_id,review_status,collection_enabled,archived_at,last_product_scan_status,last_product_scan_at FROM companies FORCE INDEX(PRIMARY) WHERE company_id IN ("+','.join(['%s']*len(ids))+")",ids)]:
   q.execute(sql,args);rows=q.fetchall()
   if rows and 'company_id' in rows[0]: print(json.dumps({'written_companies':len(rows),'invalid_eligibility':sum(r['review_status']!='verified' or r['collection_enabled']!=1 or r['archived_at'] is not None for r in rows),'statuses':{s:sum(r['last_product_scan_status']==s for r in rows) for s in ['complete','partial','failed',None]},'missing_scan_timestamp':sum(r['last_product_scan_at'] is None for r in rows)}))
   else:print(json.dumps(rows,default=str))
finally:c.close()
