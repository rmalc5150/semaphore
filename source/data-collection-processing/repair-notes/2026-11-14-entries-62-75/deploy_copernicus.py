import json,hashlib
from pathlib import Path
from ops import remote,M7,T3,session,B,BASE,P
raw=Path('copernicus_capture.py').read_bytes();sha=hashlib.sha256(raw).hexdigest();key='research-data/constellation-backfill/deployments/entries-62-75-20261114/'+sha+'/copernicus_capture.py';session.client('s3').put_object(Bucket=B,Key=key,Body=raw,ServerSideEncryption='AES256')
code='''import boto3,hashlib,os,json
from pathlib import Path
raw=boto3.client('s3',region_name='us-east-1').get_object(Bucket=BUCKET,Key=KEY)['Body'].read();assert hashlib.sha256(raw).hexdigest()==SHA;compile(raw,'copernicus_capture.py','exec');installed=[]
for folder in ROOTS:
 root=Path(folder)
 if not root.exists():continue
 p=root/'copernicus_capture.py';tmp=p.with_suffix('.6275.tmp');tmp.write_bytes(raw);os.chown(tmp,1000,1000);tmp.replace(p);installed.append(str(p))
print(json.dumps({'sha256':SHA,'installed':installed}))
'''.replace('BUCKET',repr(B)).replace('KEY',repr(key)).replace('SHA',repr(sha))
for host,instance,roots in [('m7',M7,['/opt/constellation/legacy/constellation-specialist-copernicus_era5_era5_land.service','/opt/constellation/auxiliary-publication/source','/opt/constellation/source']),('t3',T3,[str(Path.cwd()),str(Path.cwd()/'constellation/daily-workspaces/copernicus_era5_era5_land')])]:
 r=remote(instance,code.replace('ROOTS',repr(roots)));(P/('copernicus-deployment-'+host+'.json')).write_text(r['out']);print(host,r['out'],flush=True)
lanes=json.loads((P/'source-lanes.json').read_text());bad=[j for key,v in lanes['copernicus_era5_era5_land']['schedulers'].items()if '/daily-api-'in key for j in v['jobs'].values()if j.get('reason')=='source_http_404'];job=max(bad,key=lambda j:j['last_attempt'])['job'];(P/'copernicus-recovery-job.json').write_text(json.dumps(job))
session.client('s3').put_object(Bucket=B,Key=BASE+'copernicus-recovery-job.json',Body=json.dumps(job).encode(),ServerSideEncryption='AES256')
