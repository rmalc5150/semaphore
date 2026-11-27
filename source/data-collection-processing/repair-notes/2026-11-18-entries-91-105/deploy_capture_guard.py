from ops import *
import hashlib
raw=Path('public_source_capture.py').read_bytes();sha=hashlib.sha256(raw).hexdigest();key=BASE+'deployment/'+sha+'/public_source_capture.py';session.client('s3').put_object(Bucket=B,Key=key,Body=raw,ServerSideEncryption='AES256')
code=r'''import json,hashlib,boto3,os
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');raw=s.get_object(Bucket=BUCKET,Key=KEY)['Body'].read();assert hashlib.sha256(raw).hexdigest()==SHA;compile(raw,'public_source_capture.py','exec')
for root in roots:
 if not root.exists():continue
 p=root/'public_source_capture.py';tmp=p.with_name(p.name+'.provider-guard');tmp.write_bytes(raw);os.chown(tmp,1000,1000);tmp.replace(p)
print('Provider-specific URL helper is now loaded only for that provider; public capture no longer depends on an unrelated helper.')
'''.replace('BUCKET',repr(B)).replace('KEY',repr(key)).replace('SHA',repr(sha))
roots="[Path('/opt/constellation/metadata-engine-runtime'),Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/source'),*[Path('/opt/constellation/legacy')/('constellation-public-'+source+'.service')for source in "+repr(list(SOURCES))+"]]"
print(remote(M7,'from pathlib import Path\nroots='+roots+'\n'+code)['out']);print(remote(T3,'from pathlib import Path\nroots=[Path.cwd()]\n'+code)['out'])
