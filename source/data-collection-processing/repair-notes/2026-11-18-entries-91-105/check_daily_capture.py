from ops import *
code=r'''import os,json,boto3
os.environ['CONSTELLATION_ROLE']='controller';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
from constellation.control import Control
import public_source_capture as pc
c=Control();assert c.daily_allowed();updates={r['source']:r for r in json.load(open('config/constellation-public-sources.json'))['sources']};out={}
for source in SOURCES:
 spec=updates.get(source)
 if not spec or not spec.get('enabled',True)or spec.get('daily_execution')=='worker':continue
 try:
  report=pc.run(spec,'daily',limit=2,s3=c.s3);out[source]={k:report[k]for k in ('source','mode','captured_urls','remaining_urls','failed_urls','route_drained')}
 except Exception as e:out[source]={'error':type(e).__name__+':'+str(e)[:250]}
 c.s3.put_object(Bucket=BUCKET,Key=BASE+'daily-capture-check.json',Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256');print(source,out[source],flush=True)
'''.replace('SOURCES',repr(SOURCES)).replace('BUCKET',repr(B)).replace('BASE',repr(BASE))
r=remote(T3,code);print(r['out']);(P/'daily-capture-check.json').write_bytes(session.client('s3').get_object(Bucket=B,Key=BASE+'daily-capture-check.json')['Body'].read())
