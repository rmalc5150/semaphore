import sys,json,boto3
from pathlib import Path
sys.path.insert(0,'/home/ec2-user/data-collection-processing')
from company_catalogue_pipeline import connection
ids=sorted({x['company_id'] for f in Path('/home/ec2-user/product-web-rebuild').glob('batch-*.receipt.json') for x in json.loads(f.read_text())['manifest']['companies']})
c=connection(boto3.Session(region_name='us-east-1'),False)
try:
 with c.cursor() as q:
  q.execute('SELECT company_id,canonical_name,review_status,collection_enabled,archived_at,last_product_scan_at FROM companies FORCE INDEX(PRIMARY) WHERE company_id IN ('+','.join(['%s']*len(ids))+')',ids)
  print(json.dumps([r for r in q.fetchall() if r['review_status']!='verified' or r['collection_enabled']!=1 or r['archived_at'] is not None],default=str))
finally:c.close()
