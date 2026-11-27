import boto3,json,os,hashlib
from pathlib import Path
raw=boto3.client('s3').get_object(Bucket='data-collection-059416028963-us-east-1-an',Key='research-data/constellation-backfill/deployments/pdf-fallback-20261118/3a8267fd901b482cac2ffb3d15868d5a24c0e7a90e1a8472266a812385436dec/pdf_proxy_fallback.py')['Body'].read();assert hashlib.sha256(raw).hexdigest()=='3a8267fd901b482cac2ffb3d15868d5a24c0e7a90e1a8472266a812385436dec';compile(raw,'pdf_proxy_fallback.py','exec');cfg={'enabled': False, 'secret_id': 'arn:aws:secretsmanager:us-east-1:059416028963:secret:proxies-fkWzVV', 'max_requests_per_day': 4, 'max_pdf_bytes': 8388608, 'max_requests_per_client': 1, 'policy': 'Public HTTPS PDFs only. Existing downloader and one ordinary HTTPS attempt before paid proxy. Verified cache first after direct failure. One paid attempt per URL per UTC day; failures count. Reserve maximum bytes before use. Never forward API credentials.', 'allowed_sources': ['biorxiv_medrxiv_preprints']}
roots=[Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/capture-workers/source'),Path('/opt/constellation/legacy/constellation-specialist-biorxiv_medrxiv_preprints.service')]
for root in roots:
 assert (root/'regulatory_collection.py').is_file()
 for name,body in [('pdf_proxy_fallback.py',raw),('config/pdf-proxy-fallback.json',json.dumps(cfg,indent=2).encode())]:
  target=root/name;tmp=target.with_suffix('.limited.tmp');tmp.write_bytes(body);os.chmod(tmp,0o644);tmp.replace(target)
print(json.dumps({'roots':len(roots),'allowed_sources':cfg['allowed_sources'],'enabled':cfg['enabled']}))
