import json,time
from collection_storage import StorageSettings
from research_contract import ROOT,load_json
from specialist_inputs import collect
from metadata_engine.runtime_db import Database
cfg=load_json(ROOT/'config/metadata-engine.json');db=Database(cfg);s=db.session.client('s3');b=cfg['bucket'];base='research-data/constellation-backfill/repairs/entries-62-75-20261114/'
job=json.loads(s.get_object(Bucket=b,Key=base+'copernicus-recovery-job.json')['Body'].read());settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();universe=load_json(ROOT/'config/company-universe.v0.5.json');taxonomy=load_json(ROOT/'config/sectors.v1.json');out={'job':job,'passes':[]}
for _ in range(2):
 result=collect(job,store,settings,universe,taxonomy,1);out['passes'].append(result)
 s.put_object(Bucket=b,Key=base+'copernicus-recovery.json',Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256');print(json.dumps(result),flush=True)
 if result['status']in ('failed','complete'):break
