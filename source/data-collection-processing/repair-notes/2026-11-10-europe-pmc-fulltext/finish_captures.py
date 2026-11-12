import json,tempfile
from pathlib import Path
from collection_storage import StorageSettings
from metadata_engine.runtime_db import Database,fingerprint
from specialist_publication import bridge_drugsfda_inventory
from window_publication import list_keys,publish_pending
from source_observation_athena import prepare
p=Path(__file__).parent;cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();entries=[];ids=[]
for key in list_keys(store,settings,'constellation-backfill/specialist-publication-queue/epmc-fulltext/'):
 entry=json.loads(store.get(key).body);m=json.loads(store.get(entry['manifests'][0]).body)
 if m['task']['source']!='europe_pmc_fulltext':continue
 entries.append(entry)
 for page in m['pages']:
  for batch in page['batches']:
   rawkey='research-data/'+batch['key'];etag=db.session.client('s3').head_object(Bucket=cfg['bucket'],Key=rawkey)['ETag'];db.enqueue('europe_pmc_fulltext',rawkey,etag,'legacy_batch',250);ids.append(fingerprint(['europe_pmc_fulltext',rawkey,etag,'legacy_batch','2.0.3']))
(p/'daily-replay.json').write_text(json.dumps({'repair_job_ids':ids},indent=2));(p/'daily-windows.json').write_text(json.dumps(entries,indent=2));script=(p/'replay.py').read_text().replace("p/'migration.json'","p/'daily-replay.json'").replace('replay-v1','daily-replay-v1');(p/'replay_daily.py').write_text(script)
print('metadata batches',len(ids),'bridge',bridge_drugsfda_inventory(store,settings),flush=True)
c={'owner':'specialists','database':'optima_specialist_inputs','workgroup':'optima-specialist-inputs','region':settings.region,'curated_prefix':'curated/specialists/releases','query_results_prefix':'athena-results/specialists','dataset':'specialist_inputs','coverage_note':'Original full JATS articles discovered from configured Europe PMC research topics; not all literature, supplements or historical vintages.','allowed_sources':['europe_pmc_fulltext']}
def build(s,settings,config,manifests,root):return prepare(s,settings,{**config,'source_manifests':manifests},root)
with tempfile.TemporaryDirectory(prefix='epmc-fulltext-publication-') as tmp:r=publish_pending(store,settings,'specialists',c,build,Path(tmp),max_windows=len(entries),window_ids=[e['window_id'] for e in entries])
(p/'daily-publication.json').write_text(json.dumps(r,indent=2));print(r,flush=True)
assert r['status']=='complete' and all(x['status'] in ('verified','already_verified')for x in r['results'])
receipts=[]
for entry in entries:
 receipt=json.loads(store.get('operations/specialists/publication-receipts/'+entry['window_id']+'.json').body);assert receipt['status']=='verified';receipts.append(receipt)
(p/'verified-window-receipts.json').write_text(json.dumps(receipts,indent=2))
print('Verified receipts',len(receipts),flush=True)
