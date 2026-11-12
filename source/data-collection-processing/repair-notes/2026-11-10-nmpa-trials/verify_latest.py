import json,io
from pathlib import Path
from collection_storage import StorageSettings
from window_publication import list_keys
from metadata_engine.runtime_db import Database,fingerprint
from metadata_engine.evidence import evidence_for
p=Path(__file__).parent;cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();cache={}
class Cache:
 def get_object(self,**kw):
  key=kw['Key']
  if key not in cache:
   r=s.get_object(**kw);cache[key]=r['Body'].read();r['Body'].close()
  return {'Body':io.BytesIO(cache[key]),'ContentLength':len(cache[key])}
reader=Cache();out=[];ids=[]
receipts=[json.loads(store.get(k).body)for k in list_keys(store,settings,'constellation-backfill/legacy-operation-receipts/nmpa-resumed/trials/')]
for receipt in sorted(receipts,key=lambda r:r['at'],reverse=True)[:4]:
 if receipt['status']!='captured':continue
 manifest=json.loads(store.get(receipt['manifest']).body);counts={};total=0
 for page in manifest['pages']:
  for batch in page['batches']:
   k='research-data/'+batch['key'];rows=[json.loads(l)for l in store.get(batch['key']).body.splitlines()]
   for r in rows:
    artifacts=evidence_for(r,cfg['contracts']['nmpa_trials'],reader,cfg['bucket']);assert artifacts;kind=r['payload']['record_type'];counts[kind]=counts.get(kind,0)+1;total+=1
   etag=s.head_object(Bucket=cfg['bucket'],Key=k)['ETag'];db.enqueue('nmpa_trials',k,etag,'legacy_batch',250);ids.append(fingerprint(['nmpa_trials',k,etag,'legacy_batch','2.0.3']))
 out.append({**receipt,'verified_rows':total,'record_types':counts});print(out[-1],flush=True)
assert out,'No fresh captures available';(p/'fresh-captures.json').write_text(json.dumps(out,indent=2));(p/'fresh-replay.json').write_text(json.dumps({'repair_job_ids':ids},indent=2));script=(p/'replay.py').read_text().replace("p/'migration.json'","p/'fresh-replay.json'").replace('replay-v1','latest-replay-v1');(p/'replay_fresh.py').write_text(script)
