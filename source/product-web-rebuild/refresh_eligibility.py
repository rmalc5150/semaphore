import sys,json,boto3
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
sys.path.insert(0,'/home/ec2-user/data-collection-processing')
from company_catalogue_pipeline import connection
c=connection(boto3.Session(region_name='us-east-1'),False)
try:
 with c.cursor() as q:
  q.execute('SET SESSION max_execution_time=30000')
  q.execute("SELECT company_id,canonical_name,website_url,last_product_scan_at,last_product_scan_status FROM companies FORCE INDEX(PRIMARY) WHERE review_status='verified' AND collection_enabled=1 AND archived_at IS NULL ORDER BY company_id")
  rows=q.fetchall()
 stamp=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H%M%SZ')
 target=Path(__file__).resolve().parent/('eligible-'+stamp+'.json')
 target.write_text(json.dumps(rows,default=str,indent=2))
 print(json.dumps({'observed_at_utc':stamp,'eligible':len(rows),'never_scanned':sum(r['last_product_scan_at'] is None for r in rows),'statuses':dict(Counter(r['last_product_scan_status'] or 'never_scanned' for r in rows)),'snapshot':str(target)}))
finally:
 c.rollback();c.close()
