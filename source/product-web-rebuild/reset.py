import sys,json,boto3
from pathlib import Path
sys.path.insert(0,'/home/ec2-user/data-collection-processing')
from company_catalogue_pipeline import connection
assert not Path('/home/ec2-user/product-web-rebuild/reset-completed.json').exists(),'Reset already completed; refusing to erase researched products'
c=connection(boto3.Session(region_name='us-east-1'),False)
try:
 with c.cursor() as q:
  q.execute("SELECT GET_LOCK('optima_product_catalogue_v1',0) AS acquired");assert q.fetchone()['acquired']==1
  q.execute('SET @app_actor=%s,@app_change_reason=%s',('direct-web-product-rebuild/2026-10-20','User approved clearing all products and prior scan metadata without backup for direct web rebuild'))
  q.execute("SELECT TABLE_NAME,COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE WHERE REFERENCED_TABLE_SCHEMA='tracking' AND REFERENCED_TABLE_NAME='products'")
  refs=q.fetchall();allowed={'products','product_companies','product_aliases','product_identifiers','product_contexts','person_products'}
  assert all(r['TABLE_NAME'] in allowed for r in refs),refs
  counts={}
  for table in ['person_products','product_contexts','product_identifiers','product_aliases','product_companies']:
   q.execute('SELECT COUNT(*) n FROM information_schema.tables WHERE table_schema=%s AND table_name=%s',('tracking',table))
   if q.fetchone()['n']:
    q.execute('DELETE FROM '+table);counts[table]=q.rowcount
  q.execute('UPDATE products SET parent_product_id=NULL WHERE parent_product_id IS NOT NULL')
  q.execute('DELETE FROM products');counts['products']=q.rowcount
  q.execute('UPDATE companies SET last_product_scan_at=NULL,last_product_scan_status=NULL,last_product_scan_error=NULL,last_product_scan_evidence=NULL WHERE last_product_scan_at IS NOT NULL OR last_product_scan_status IS NOT NULL OR last_product_scan_error IS NOT NULL OR last_product_scan_evidence IS NOT NULL');counts['reset_company_scans']=q.rowcount
  q.execute('SELECT COUNT(*) n FROM products');assert q.fetchone()['n']==0
 c.commit()
 with c.cursor() as q:
  q.execute("SELECT company_id,canonical_name,website_url,sector_ids FROM companies WHERE review_status='verified' AND collection_enabled=1 AND archived_at IS NULL ORDER BY company_id")
  cohort=q.fetchall()
 Path('/home/ec2-user/product-web-rebuild/cohort.json').write_text(json.dumps(cohort,default=str,indent=2))
 print(json.dumps({'deleted':counts,'eligible_companies':len(cohort),'first_companies':cohort[:12]},default=str))
finally:c.rollback();c.close()
