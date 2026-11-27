import json
from ops import session,B,BASE,P
s=session.client('s3')
for name in ['statistics-capture.json','other-raw-validation.json','replay-publication.json']:
 try:
  raw=s.get_object(Bucket=B,Key=BASE+name)['Body'].read();(P/name).write_bytes(raw);d=json.loads(raw)
  if name=='statistics-capture.json':print(name,json.dumps(d))
  elif name=='other-raw-validation.json':print(name,[(x['source'],x.get('dataset'),x['status'],x.get('reason'))for x in d])
  else:print(name,d['processed'],{source:entry['control']for source,entry in d['sources'].items()})
 except s.exceptions.NoSuchKey:print(name,'pending')
