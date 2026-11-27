from ops import *
code=r'''import json,uuid,boto3
from datetime import datetime,timezone
s=boto3.client('s3',region_name='us-east-1');b=BUCKET;base=BASE;prefix='research-data/constellation-backfill/daily-api-runtime/';source='cninfo_mainland_china_company_disclosures';key=prefix+source+'/current.json';old=s.get_object(Bucket=b,Key=key);current=json.loads(old['Body'].read());assert not current.get('paths'),'Do not overwrite an active or nonempty source runtime'
seed=json.loads(s.get_object(Bucket=b,Key=prefix+'south_korea_fss_opendart/current.json')['Body'].read());paths={k:v for k,v in seed['paths'].items()if k in ('config/company-universe.v0.2.json','config/company-universe.v0.3.json','config/company-universe.v0.5.json')};assert 'config/company-universe.v0.5.json'in paths
s.put_object(Bucket=b,Key=base+'cninfo-daily-index-before-seed.json',Body=json.dumps(current).encode(),ServerSideEncryption='AES256')
run='cninfo-bootstrap-'+uuid.uuid4().hex;index={**current,'paths':paths,'unit':'constellation-public-api-'+source+'.service','run_id':run,'recorded_at':datetime.now(timezone.utc).isoformat()};raw=json.dumps(index,sort_keys=True).encode()
s.put_object(Bucket=b,Key=prefix+source+'/manifests/'+run+'.json',Body=raw,ServerSideEncryption='AES256',IfNoneMatch='*');s.put_object(Bucket=b,Key=key,Body=raw,ServerSideEncryption='AES256',IfMatch=old['ETag']);print(json.dumps({'seeded_source':source,'configuration_files':list(paths),'copied_collector_state':False}))
'''.replace('BUCKET',repr(B)).replace('BASE',repr(BASE))
print(remote(T3,code)['out'])
