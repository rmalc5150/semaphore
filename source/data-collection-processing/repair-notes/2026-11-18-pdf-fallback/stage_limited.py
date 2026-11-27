from pathlib import Path
import boto3,json,hashlib
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';body=Path('pdf_proxy_fallback.py').read_bytes();sha=hashlib.sha256(body).hexdigest();key='research-data/constellation-backfill/deployments/pdf-fallback-20261118/'+sha+'/pdf_proxy_fallback.py';s.put_object(Bucket=b,Key=key,Body=body,ServerSideEncryption='AES256');cfg=json.load(open('config/pdf-proxy-fallback.json'))
script='''import boto3,json,os,hashlib
from pathlib import Path
raw=boto3.client('s3').get_object(Bucket=BUCKET,Key=KEY)['Body'].read();assert hashlib.sha256(raw).hexdigest()==SHA;compile(raw,'pdf_proxy_fallback.py','exec');cfg=CONFIG
roots=[Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/capture-workers/source'),Path('/opt/constellation/legacy/constellation-specialist-biorxiv_medrxiv_preprints.service')]
for root in roots:
 assert (root/'regulatory_collection.py').is_file()
 for name,body in [('pdf_proxy_fallback.py',raw),('config/pdf-proxy-fallback.json',json.dumps(cfg,indent=2).encode())]:
  target=root/name;tmp=target.with_suffix('.limited.tmp');tmp.write_bytes(body);os.chmod(tmp,0o644);tmp.replace(target)
print(json.dumps({'roots':len(roots),'allowed_sources':cfg['allowed_sources'],'enabled':cfg['enabled']}))
'''.replace('BUCKET',repr(b)).replace('KEY',repr(key)).replace('SHA',repr(sha)).replace('CONFIG',repr(cfg));(p/'deploy_limited.py').write_text(script)
