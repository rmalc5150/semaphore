from ops import *
s=session.client('s3')
for name in ['migration.json','replay-publication.json','final-opinions.json']:
 try:
  raw=s.get_object(Bucket=B,Key=BASE+name)['Body'].read();(P/name).write_bytes(raw);v=json.loads(raw)
  if name=='replay-publication.json':print(name,json.dumps(v,default=str))
  elif name=='final-opinions.json':print(name,[(r['source'],r['status'],r.get('reason'))for r in v])
 except s.exceptions.NoSuchKey:print(name,'pending')
print(remote(T3,"from constellation.control import Control;from constellation.historical_guard import dispatch_guard;c=Control();print(c.get());print('allowed',c.allowed());\nwith dispatch_guard(c)as acquired:print('dispatch_guard',acquired)")['out'])
