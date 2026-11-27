import hashlib
from pathlib import Path
from ops import session,remote,M7,B,P
raw=Path('metadata_engine/public_statistics.py').read_bytes();sha=hashlib.sha256(raw).hexdigest();key='research-data/constellation-backfill/deployments/entries-62-75-20261114/'+sha+'/public_statistics.py';session.client('s3').put_object(Bucket=B,Key=key,Body=raw,ServerSideEncryption='AES256')
print(remote(M7,'''import boto3,hashlib,subprocess,os
from pathlib import Path
raw=boto3.client('s3',region_name='us-east-1').get_object(Bucket=BUCKET,Key=KEY)['Body'].read();assert hashlib.sha256(raw).hexdigest()==SHA
roots=[Path('/opt/constellation/metadata-engine-runtime'),Path('/opt/constellation/auxiliary-publication/source')]+[Path('/opt/constellation/legacy/constellation-specialist-'+source+'.service')for source in ('unido_iip_and_indstat','imf_portwatch_shipping_activity')]
for root in roots:
 p=root/'metadata_engine/public_statistics.py';tmp=p.with_suffix('.6275.tmp');tmp.write_bytes(raw);os.chown(tmp,1000,1000);tmp.replace(p)
subprocess.run(['systemctl','stop','optima-native-statistics-proof-v2-20261114.service'],check=False)
print('Installed bounded original-response cache; stopped only the temporary proof runner for a checkpointed retry.')
'''.replace('BUCKET',repr(B)).replace('KEY',repr(key)).replace('SHA',repr(sha))))
