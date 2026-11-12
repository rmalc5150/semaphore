"""Complete owner-authorized retirement without deleting captured evidence."""
import ast
import base64
import hashlib
import io
import json
import tarfile
from pathlib import Path
from constellation.finish_aux_migration import remote, T3, M7, ROOT, session
from constellation.retire_tracking import FILES

BUCKET='data-collection-059416028963-us-east-1-an'

def source_inventory():
    paths=[ROOT/name for name in FILES]
    names={Path(name).stem for name in FILES}
    for p in ROOT.glob('test_*.py'):
        tree=ast.parse(p.read_text())
        imports={n.module.split('.')[0] for n in ast.walk(tree)if isinstance(n,ast.ImportFrom)and n.module}|{a.name.split('.')[0]for n in ast.walk(tree)if isinstance(n,ast.Import)for a in n.names}
        if imports & names:paths.append(p)
    for p in (ROOT/'systemd').glob('*'):
        if p.is_file() and (any(name in p.read_text()for name in FILES)or any(p.name.startswith(unit)for unit in ('optima-company-','optima-product-catalogue-'))):paths.append(p)
    paths.append(ROOT/'constellation/provision_processing_login.py')
    paths.extend(p.with_suffix('.timer')for p in list(paths)if p.suffix=='.service'and p.with_suffix('.timer').is_file())
    return sorted(set(p for p in paths if p.is_file()))

def main():
    paths=source_inventory();buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w:gz')as tar:
        for p in paths:tar.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
    body=buf.getvalue();sha=hashlib.sha256(body).hexdigest();key='research-data/constellation-backfill/retirements/tracking/controller-source-'+sha+'.tgz'
    s=session.client('s3');s.put_object(Bucket=BUCKET,Key=key,Body=body,ServerSideEncryption='AES256')
    assert hashlib.sha256(s.get_object(Bucket=BUCKET,Key=key)['Body'].read()).hexdigest()==sha
    (ROOT/'constellation/migration/tracking-source-removal.json').write_text(json.dumps({'paths':[str(p.relative_to(ROOT))for p in paths],'archive':key},indent=2))
    payload={name:base64.b64encode((ROOT/name).read_bytes()).decode()for name in ('usgs_minerals_enrichment.py','bls_evidence_joins.py','product_search_daily.py','product_search_runner.py','product_search_directory.py')}
    raw=json.dumps(payload).encode();payload_sha=hashlib.sha256(raw).hexdigest();payload_key='research-data/constellation-backfill/deployments/registry-retirement-'+payload_sha+'.json'
    s.put_object(Bucket=BUCKET,Key=payload_key,Body=raw,ServerSideEncryption='AES256')
    for instance in (M7,T3):
        remote(instance,'''from pathlib import Path
import json,subprocess,io,tarfile,boto3,hashlib,os,base64
base=Path(__BASE__);files=__FILES__
raw=boto3.client('s3',region_name='us-east-1').get_object(Bucket=__BUCKET__,Key=__PAYLOAD_KEY__)['Body'].read();assert hashlib.sha256(raw).hexdigest()==__PAYLOAD_SHA__;payload=json.loads(raw)
receipt_path=base/('constellation/migration/tracking-retirement.json'if __T3__ else 'tmp/tracking-retirement.json')
receipt=json.loads(receipt_path.read_text());units=[u for u in receipt['retired_units']if u!='optima-product-search-daily.service']
roots=([base,*list((base/'constellation/daily-workspaces').glob('*'))]if __T3__ else [base/'source',base/'auxiliary-publication/source',base/'research-publication/source',base/'metadata-engine-runtime',*list((base/'legacy').glob('*'))])
archive=io.BytesIO()
with tarfile.open(fileobj=archive,mode='w:gz',dereference=True)as tar:
 for unit in units:
  for name in (unit,unit.removesuffix('.service')+'.timer'):
   p=Path('/etc/systemd/system')/name
   if p.is_file()and not p.is_symlink():tar.add(p,arcname=str(p).lstrip('/'),recursive=False)
body=archive.getvalue();sha=hashlib.sha256(body).hexdigest();key='research-data/constellation-backfill/retirements/tracking/'+('t3'if __T3__ else 'm7')+'-units-'+sha+'.tgz';s=boto3.client('s3',region_name='us-east-1');s.put_object(Bucket=__BUCKET__,Key=key,Body=body,ServerSideEncryption='AES256');assert hashlib.sha256(s.get_object(Bucket=__BUCKET__,Key=key)['Body'].read()).hexdigest()==sha
for unit in units:
 for name in (unit,unit.removesuffix('.service')+'.timer'):
  subprocess.run(['systemctl','disable','--now',name],capture_output=True)
  p=Path('/etc/systemd/system')/name
  p.unlink(missing_ok=True);p.symlink_to('/dev/null')
for root in roots:
 if not root.is_dir():continue
 for name,encoded in payload.items():
  p=root/name
  if not p.exists()and name not in ('product_search_daily.py','product_search_runner.py'):continue
  if not p.exists()and not (root/'product_search_directory.py').exists():continue
  tmp=p.with_suffix('.retirement');tmp.write_bytes(base64.b64decode(encoded));os.chown(tmp,1000,1000);tmp.replace(p)
 cfg=root/'config/constellation-legacy-routes.json'
 if cfg.is_file():
  data=json.loads(cfg.read_text());data['routes']=[r for r in data['routes']if not any(n in ' '.join(r.get('argv',[]))for n in files)];tmp=cfg.with_suffix('.retirement');tmp.write_text(json.dumps(data,indent=2));os.chown(tmp,1000,1000);tmp.replace(cfg)
subprocess.run(['systemctl','daemon-reload'],check=True)
for unit in units:subprocess.run(['systemctl','reset-failed',unit],capture_output=True)
if __T3__:
 for name in ('optima-product-search-daily.service','optima-product-search-daily.timer'):
  p=Path('/etc/systemd/system')/name
  if p.is_symlink()and str(p.readlink())=='/dev/null':p.unlink()
 subprocess.run(['systemctl','daemon-reload'],check=True)
 subprocess.run(['systemctl','enable','--now','optima-product-search-daily.timer'],check=True)
 subprocess.run(['systemctl','start','--no-block','optima-product-search-daily.service'],check=True)
receipt['retired_units']=units;receipt['unit_archive']=key;receipt['product_search_preserved']=True;receipt_path.write_text(json.dumps(receipt,indent=2))
print(json.dumps({'persistent_masks':units,'unit_archive':key,'product_search_preserved':True}))
'''.replace('__BASE__',repr(str(ROOT)if instance==T3 else '/opt/constellation')).replace('__FILES__',repr(FILES)).replace('__PAYLOAD_KEY__',repr(payload_key)).replace('__PAYLOAD_SHA__',repr(payload_sha)).replace('__T3__',repr(instance==T3)).replace('__BUCKET__',repr(BUCKET)))
    from constellation.control import Control
    routes=json.loads((ROOT/'config/constellation-legacy-routes.json').read_text())
    old=json.loads((ROOT/'constellation/migration/tracking-retirement.json').read_text())['retired_units']
    with Control().db()as c:
        updated=0
        for unit in old:
            c.execute("UPDATE backfill_jobs SET status='blocked',result_json=%s,lease_until=0,lease_token=NULL,updated_at=UNIX_TIMESTAMP() WHERE source_key=%s AND status IN ('pending','running','retryable_failed','blocked')",(json.dumps({'reason':'owner_retired_registry','deliberately_retired':True,'coverage_status':'not_applicable'}),'legacy:'+unit))
            updated+=c.rowcount
    # The failed provisioning attempt created only a USAGE login. Remove only that known unused login.
    from rds_management_access import settings
    from metadata_engine_provision import mysql
    aws,db,admin,_=settings()
    grants=mysql(db,admin,"SHOW GRANTS FOR 'optima_processing_worker'@'%';")
    assert all(line.startswith('GRANT USAGE ON *.*')for line in grants.splitlines()),'Unexpected processing login grants; manual review required'
    mysql(db,admin,"DROP USER 'optima_processing_worker'@'%';")
    aws.client('secretsmanager').delete_secret(SecretId='optima/m7-processing',RecoveryWindowInDays=7)
    print(json.dumps({'retired_queue_jobs':updated,'source_archive':key,'source_deletions_ready':len(paths),'unused_login_removed':True}))

if __name__=='__main__':main()
