import json,tempfile
from pathlib import Path
from collection_storage import StorageSettings
from metadata_engine.runtime_db import Database,fingerprint
from specialist_publication import publication_config
from source_observation_athena import prepare
from window_publication import publish_pending
p=Path(__file__).parent;settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();state=json.loads(store.get('constellation-backfill/cms-payments/catalog-state.json').body);assert state['status']=='complete';entry=json.loads(store.get('constellation-backfill/specialist-publication-queue/cms-payments/'+state['window_id']+'.json').body);(p/'fresh-catalog.json').write_text(json.dumps(state,indent=2));m=json.loads(store.get(state['manifest']).body);cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);ids=[]
for page in m['pages']:
 for batch in page['batches']:
  key='research-data/'+batch['key'];etag=db.session.client('s3').head_object(Bucket=cfg['bucket'],Key=key)['ETag'];db.enqueue('cms_payments_catalog',key,etag,'legacy_batch',250)
  n=len(store.get(batch['key']).body.splitlines())
  for offset in range(0,n,32):ids.append(fingerprint(['cms_payments_catalog',key,etag,'legacy_batch'+('@'+str(offset)if offset else''),'2.0.3']))
(p/'daily-replay.json').write_text(json.dumps({'repair_job_ids':ids}));script=(p/'replay.py').read_text().replace("p/'migration.json'","p/'daily-replay.json'").replace('replay-v1','daily-replay-v1');(p/'replay_daily.py').write_text(script)
target='operations/specialists/publication-queue/'+entry['window_id']+'.json'
if store.get(target)is None:
 from collection_storage import write_json
 write_json(store,target,entry)
c=publication_config(settings,json.load(open('config/specialist-inputs.json')))
def build(s,settings,config,manifests,root):return prepare(s,settings,{**config,'source_manifests':manifests},root)
with tempfile.TemporaryDirectory(prefix='cms-catalog-publication-')as tmp:r=publish_pending(store,settings,'specialists',c,build,Path(tmp),max_windows=1,window_ids=[entry['window_id']])
(p/'fresh-publication.json').write_text(json.dumps(r,indent=2));receipt=json.loads(store.get('operations/specialists/publication-receipts/'+entry['window_id']+'.json').body);assert receipt['status']=='verified';(p/'fresh-verification-receipt.json').write_text(json.dumps(receipt,indent=2));print('Verified fresh catalog',state['records'],entry['window_id'],flush=True)
