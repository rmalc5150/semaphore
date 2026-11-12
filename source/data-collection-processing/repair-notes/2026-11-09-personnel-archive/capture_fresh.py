import json
from pathlib import Path
from collection_storage import StorageSettings
from personnel_archive import collect
from metadata_engine.runtime_db import Database,fingerprint
p=Path(__file__).parent;settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();key='manifests/collection_runs/source=people_rss/dataset=people_source_records/run_be62ee0f-fb2e-4845-b7e8-0ba586506679/final.json';result=collect(store,settings,key);(p/'fresh-capture.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
assert result['status']=='complete';m=json.loads(store.get(result['manifest']).body);db=Database(json.load(open('config/metadata-engine.json')));s=db.session.client('s3');migration=json.loads((p/'migration.json').read_text())
for page in m['pages']:
 for b in page['batches']:
  raw_key='research-data/'+b['key'];etag=s.head_object(Bucket=settings.s3_bucket,Key=raw_key)['ETag'];db.enqueue('personnel_archive',raw_key,etag,'legacy_batch',400);migration['repair_job_ids'].append(fingerprint(['personnel_archive',raw_key,etag,'legacy_batch','2.0.3']))
(p/'migration.json').write_text(json.dumps(migration,indent=2))
