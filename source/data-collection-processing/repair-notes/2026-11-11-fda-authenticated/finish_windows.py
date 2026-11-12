import json,tempfile,fcntl
from pathlib import Path
from collection_storage import StorageSettings,write_json
from metadata_engine.runtime_db import Database,fingerprint
from metadata_engine.evidence import evidence_for
from specialist_publication import publication_config
from source_observation_athena import prepare
from window_publication import list_keys,publish_pending
from metadata_engine.fda_authenticated import SOURCES
p=Path(__file__).parent;settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);entries=[];ids={s:[]for s in SOURCES};counts={};s3=db.session.client('s3')
for key in list_keys(store,settings,'constellation-backfill/specialist-publication-queue/fda-review/'):
 entry=json.loads(store.get(key).body);m=json.loads(store.get(entry['manifests'][0]).body);source=m['task']['source']
 if source not in SOURCES:continue
 entries.append(entry);counts[source]=counts.get(source,0)+m['record_count']
 for page in m['pages']:
  for batch in page['batches']:
   rawkey='research-data/'+batch['key'];etag=s3.head_object(Bucket=cfg['bucket'],Key=rawkey)['ETag'];rows=store.get(batch['key']).body.splitlines()
   # Verify all rows, including continuation rows beyond the first 32.
   for line in rows:evidence_for(json.loads(line),cfg['contracts'][source],s3,cfg['bucket'])
   db.enqueue(source,rawkey,etag,'legacy_batch',250)
   for offset in range(0,len(rows),32):ids[source].append(fingerprint([source,rawkey,etag,'legacy_batch'+('@'+str(offset)if offset else''),'2.0.3']))
 target='operations/specialists/publication-queue/'+entry['window_id']+'.json'
 if store.get(target)is None:write_json(store,target,entry)
for source,values in ids.items():
 folder=p/source;(folder/'daily-replay.json').write_text(json.dumps({'repair_job_ids':list(dict.fromkeys(values))},indent=2));script=(folder/'replay.py').read_text().replace("p/'migration.json'","p/'daily-replay.json'").replace('replay-v2','daily-replay-v2');(folder/'replay_daily.py').write_text(script)
(p/'fresh-windows.json').write_text(json.dumps(entries,indent=2));(p/'fresh-validation.json').write_text(json.dumps(counts,indent=2));print('Verified all fresh rows',counts,flush=True)
c=publication_config(settings,json.load(open('config/specialist-inputs.json')))
def build(s,settings,config,manifests,root):return prepare(s,settings,{**config,'source_manifests':manifests},root)
with Path('.specialist-publication.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 with tempfile.TemporaryDirectory(prefix='fda-review-publication-')as tmp:r=publish_pending(store,settings,'specialists',c,build,Path(tmp),max_windows=len(entries),window_ids=[e['window_id']for e in entries])
(p/'fresh-publication.json').write_text(json.dumps(r,indent=2));receipts=[json.loads(store.get('operations/specialists/publication-receipts/'+e['window_id']+'.json').body)for e in entries];assert all(x['status']=='verified'for x in receipts);(p/'fresh-receipts.json').write_text(json.dumps(receipts,indent=2));print('Verified receipts',len(receipts),flush=True)
