import sys,boto3,json
sys.path.insert(0,'/home/ec2-user/data-collection-processing')
from company_catalogue_pipeline import connection
c=connection(boto3.Session(region_name='us-east-1'),False)
try:
 with c.cursor() as q:
  q.execute('SELECT sector_id,subsector_id,COUNT(*) n FROM products GROUP BY sector_id,subsector_id ORDER BY sector_id,n DESC');print(json.dumps(q.fetchall()))
finally:c.close()
