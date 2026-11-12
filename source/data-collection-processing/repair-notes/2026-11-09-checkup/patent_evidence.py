import json,boto3
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');bucket='data-collection-059416028963-us-east-1-an';p=Path(__file__).parent
prefix='research-data/checkpoints/uspto-prosecution-documents/'
# Bound to one API listing page, then inspect the most recently saved failed records.
items=s.list_objects_v2(Bucket=bucket,Prefix=prefix,MaxKeys=1000).get('Contents',[]);out=[]
for o in sorted(items,key=lambda r:r['LastModified'],reverse=True)[:12]:
 d=json.loads(s.get_object(Bucket=bucket,Key=o['Key'])['Body'].read())
 if d.get('reason')=='official_document_not_found':
  out.append({'key':o['Key'],'receipt':d})
(p/'patent-document-failures.json').write_text(json.dumps(out,indent=2,default=str));print(json.dumps(out,default=str)[:8000])
