"""Retire owner-abandoned registry executables; preserve raw/checkpoint evidence."""
from constellation.finish_aux_migration import remote,T3,M7
FILES=['bluesky_company_daily.py','caiso_pipeline.py','company_auto_review.py','company_catalogue_pipeline.py','company_identity_evidence.py','doe_storage_pipeline.py','enrich_company_identities.py','freeze_company_enrichment_baseline.py','github_company_mapping.py','grant_pipeline.py','nist_robotics_match.py','product_catalogue_backfill.py','product_catalogue_migration.py','product_catalogue_pipeline.py','product_web_registry.py','rds_company_directory.py','review_company_catalogue.py','tracking_mysql_trial.py','tracking_people_migration.py','tracking_registry_reset.py','trade_screening_daily.py','verify_product_catalogue.py']

def retire(instance):
 remote(instance,'''from pathlib import Path
import subprocess,json,io,tarfile,boto3,hashlib,datetime,os
files=FILES
base=Path(BASE)
units=subprocess.check_output(['systemctl','list-unit-files','--type=service','--no-legend','--plain','optima-*','constellation-*'],text=True)
selected=[]
for line in units.splitlines():
 unit=line.split()[0]
 cmd=subprocess.run(['systemctl','show',unit,'-p','ExecStart','--value'],text=True,capture_output=True).stdout
 if any(name in cmd for name in files):selected.append(unit)
for unit in selected:
 timer=unit.removesuffix('.service')+'.timer'
 subprocess.run(['systemctl','disable','--now',timer],capture_output=True)
 subprocess.run(['systemctl','stop',unit],capture_output=True)
 subprocess.run(['systemctl','mask',unit],capture_output=True)
roots=[base]
if base==Path('/opt/constellation'):
 roots+=[base/'source',base/'auxiliary-publication/source',base/'research-publication/source',base/'metadata-engine-runtime',*list((base/'legacy').glob('*'))]
else:roots+=list((base/'constellation/daily-workspaces').glob('*'))
targets=[root/name for root in roots if root.is_dir()for name in files if (root/name).is_file()or(root/name).is_symlink()]
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w:gz',dereference=True)as tar:
 for p in targets:tar.add(p,arcname=str(p).lstrip('/'),recursive=False)
body=buf.getvalue();sha=hashlib.sha256(body).hexdigest();key='research-data/constellation-backfill/retirements/tracking/'+HOST+'-'+sha+'.tgz';s=boto3.client('s3',region_name='us-east-1');bucket='data-collection-059416028963-us-east-1-an';s.put_object(Bucket=bucket,Key=key,Body=body,ServerSideEncryption='AES256');assert hashlib.sha256(s.get_object(Bucket=bucket,Key=key)['Body'].read()).hexdigest()==sha
# Controller source is deleted with apply_patch after runtime retirement.
deleted=[]
for p in targets:
 if HOST=='t3'and p.parent==base:continue
 p.unlink();deleted.append(str(p))
for root in roots:
 cfg=root/'config/constellation-legacy-routes.json'
 if not cfg.is_file():continue
 data=json.loads(cfg.read_text());changed=False
 for row in data['routes']:
  if any(name in ' '.join(row.get('argv',[])) for name in files):row.update(execution_enabled=False,remaining_requirements=['owner_retired_registry']);changed=True
 if changed:
  tmp=cfg.with_suffix('.retirement');tmp.write_text(json.dumps(data,indent=2));os.chown(tmp,1000,1000);tmp.replace(cfg)
receipt={'retired_units':selected,'removed_runtime_files':deleted,'recovery_archive':'s3://'+bucket+'/'+key,'raw_data_deleted':False}
out=base/'constellation/migration'if HOST=='t3'else base/'tmp';out.mkdir(parents=True,exist_ok=True);(out/'tracking-retirement.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({'retired_units':selected,'removed_files':len(deleted),'archive':key}))
'''.replace('FILES',repr(FILES)).replace('BASE',repr('/home/ec2-user/data-collection-processing'if instance==T3 else '/opt/constellation')).replace('HOST',repr('t3'if instance==T3 else 'm7')))
def main():
 retire(T3);retire(M7)
if __name__=='__main__':main()
