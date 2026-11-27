import os,sys,json,fcntl
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
import boto3
from collection_storage import StorageSettings,now
from research_contract import load_json
from specialist_publication import publication_config
from source_observation_athena import prepare
from window_publication import publish_pending
s=boto3.client('s3');bucket='data-collection-059416028963-us-east-1-an';base='research-data/constellation-backfill/repairs/2026-11-16';d=json.loads(s.get_object(Bucket=bucket,Key=base+'/replay-results.json')['Body'].read());ids={r['job_id']for r in d['outcomes']if r['status']=='complete'and r.get('records')}
settings=StorageSettings.load(root/'config/collection-storage.s3.json');config=publication_config(settings,load_json(root/'config/specialist-inputs.json'))
def build(store,settings,config,manifests,out):return prepare(store,settings,{**config,'source_manifests':manifests},out)
# Serialize with the deployed auxiliary publishers as well as specialist preparation.
lock=Path('/opt/constellation/auxiliary-publication/publish.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
with(root/'.specialist-publication.lock').open('a')as own:
 fcntl.flock(own,fcntl.LOCK_EX)
 r=publish_pending(settings.store(),settings,'specialists',config,build,root/'specialist-athena-build',max_windows=len(ids),window_ids=ids)
s.put_object(Bucket=bucket,Key=base+'/publication-results.json',Body=json.dumps({'at':now(),'result':r},default=str).encode(),ServerSideEncryption='AES256');print(json.dumps(r),flush=True)
if r['status']=='failed':raise SystemExit(1)
