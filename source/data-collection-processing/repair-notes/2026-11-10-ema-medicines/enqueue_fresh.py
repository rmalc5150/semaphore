import json
from pathlib import Path
from collection_storage import StorageSettings
from metadata_engine.runtime_db import Database,fingerprint
p=Path(__file__).parent;cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);store=StorageSettings.load('config/collection-storage.s3.json').store();entry=json.load(open(p/'fresh-capture.json'));m=json.loads(store.get(entry['manifest']).body);batch=m['pages'][0]['batches'][0];key='research-data/'+batch['key'];etag=db.session.client('s3').head_object(Bucket=cfg['bucket'],Key=key)['ETag'];db.enqueue('ema_medicines',key,etag,'legacy_batch',250);identity=fingerprint(['ema_medicines',key,etag,'legacy_batch','2.0.3']);(p/'fresh-replay.json').write_text(json.dumps({'repair_job_ids':[identity]},indent=2));script=(p/'replay.py').read_text().replace("p/'migration.json'","p/'fresh-replay.json'").replace('replay-v1','fresh-replay-v1');(p/'replay_fresh.py').write_text(script)
