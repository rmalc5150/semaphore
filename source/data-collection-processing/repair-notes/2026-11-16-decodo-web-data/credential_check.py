import boto3,json,base64
from pathlib import Path
s=boto3.client('secretsmanager',region_name='us-east-1');raw=s.get_secret_value(SecretId='proxies')['SecretString'];d=json.loads(raw)
fields=sorted(d)if isinstance(d,dict)else[];candidates=[]
for k in fields:
 if 'decodo'in k.lower():
  v=d[k];basic=False
  if isinstance(v,str):
   try:basic=':'in base64.b64decode(v,validate=True).decode()
   except Exception:pass
  candidates.append({'field':k,'configured':isinstance(v,str)and bool(v.strip()),'looks_like_basic_pair':basic})
print(json.dumps({'secret':'proxies','decodo_fields':candidates}))
