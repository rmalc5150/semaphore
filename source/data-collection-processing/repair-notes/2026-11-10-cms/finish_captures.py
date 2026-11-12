import json,tempfile
from pathlib import Path
from collection_storage import StorageSettings
from metadata_engine.runtime_db import Database,fingerprint
from specialist_publication import bridge_drugsfda_inventory,publication_config
from window_publication import list_keys,publish_pending
from source_observation_athena import prepare
p=Path(__file__).parent;cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();entries=[];ids=[]
for key in list_keys(store,settings,'constellation-backfill/specialist-publication-queue/cms-coverage/'):
 entry=json.loads(store.get(key).body);m=json.loads(store.get(entry['manifests'][0]).body)
 if m['task']['source']not in ('cms_coverage','cms_coverage_documents'):continue
 entries.append(entry)
 for page in m['pages']:
  for batch in page['batches']:
   rawkey='research-data/'+batch['key'];etag=db.session.client('s3').head_object(Bucket=cfg['bucket'],Key=rawkey)['ETag'];source=m['task']['source'];db.enqueue(source,rawkey,etag,'legacy_batch',250);ids.append({'source':source,'id':fingerprint([source,rawkey,etag,'legacy_batch','2.0.3'])})
for source in ('cms_coverage','cms_coverage_documents'):
 folder=p/source
 (folder/'daily-replay.json').write_text(json.dumps({'repair_job_ids':[i['id']for i in ids if i['source']==source]},indent=2))
 script=(folder/'replay.py').read_text().replace("p/'migration.json'","p/'daily-replay.json'").replace('replay-v1','daily-replay-v1')
 (folder/'replay_daily.py').write_text(script)
(p/'daily-windows.json').write_text(json.dumps(entries,indent=2))
print('metadata batches',len(ids),'bridge',bridge_drugsfda_inventory(store,settings),flush=True)
c=publication_config(settings,json.load(open('config/specialist-inputs.json')))
def build(s,settings,config,manifests,root):return prepare(s,settings,{**config,'source_manifests':manifests},root)
with tempfile.TemporaryDirectory(prefix='cms-coverage-publication-') as tmp:r=publish_pending(store,settings,'specialists',c,build,Path(tmp),max_windows=len(entries),window_ids=[e['window_id'] for e in entries])
(p/'daily-publication.json').write_text(json.dumps(r,indent=2));print(r,flush=True)
assert r['status']=='complete' and all(x['status'] in ('verified','already_verified')for x in r['results'])
receipts=[]
for entry in entries:
 receipt=json.loads(store.get('operations/specialists/publication-receipts/'+entry['window_id']+'.json').body);assert receipt['status']=='verified';receipts.append(receipt)
(p/'verified-window-receipts.json').write_text(json.dumps(receipts,indent=2))
print('Verified receipts',len(receipts),flush=True)
