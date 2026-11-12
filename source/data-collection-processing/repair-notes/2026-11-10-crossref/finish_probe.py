import json,time,boto3,tempfile,fcntl
from pathlib import Path
from collection_storage import StorageSettings
from metadata_engine.runtime_db import Database,fingerprint
from conference_athena import prepare,bridge_resumed
from window_publication import publish_pending
p=Path(__file__).parent;settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);ssm=boto3.client('ssm',region_name='us-east-1');ref=json.load(open(p/'current-probe-command.json'));r=ssm.get_command_invocation(CommandId=ref['command_id'],InstanceId=ref['instance']);(p/'current-probe-command-result.json').write_text(json.dumps(r,indent=2,default=str));print('Probe',r['Status'],r['StandardErrorContent'][-600:],flush=True);assert r['Status']=='Success'
entry=next(json.loads(line)for line in r['StandardOutputContent'].splitlines()if line.startswith('{')and json.loads(line).get('mode')=='current_work_probe');(p/'fresh-capture.json').write_text(json.dumps(entry,indent=2));m=json.loads(store.get(entry['manifest']).body);b=m['pages'][0]['batches'][0];key='research-data/'+b['key'];etag=db.session.client('s3').head_object(Bucket=cfg['bucket'],Key=key)['ETag'];db.enqueue('crossref_proceedings',key,etag,'legacy_batch',250);ids=[fingerprint(['crossref_proceedings',key,etag,'legacy_batch','2.0.3'])]
with db.tx()as c:
 c.execute("SELECT job_id FROM engine_jobs WHERE source_key='crossref_proceedings' AND input_format='public_receipt' AND state IN ('queued','retry') LIMIT 5");ids.extend(x['job_id']for x in c.fetchall())
(p/'fresh-replay.json').write_text(json.dumps({'repair_job_ids':ids},indent=2));s=(p/'replay.py').read_text().replace("p/'migration.json'","p/'fresh-replay.json'").replace('replay-v1','fresh-replay-v1');(p/'replay_fresh.py').write_text(s)
bridge_resumed(store,settings)
with open('.conference-athena.lock','a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 with tempfile.TemporaryDirectory(prefix='crossref-probe-publication-')as tmp:result=publish_pending(store,settings,'conferences',json.load(open('config/conference-athena.json')),prepare,Path(tmp),max_windows=1,window_ids=[entry['window_id']])
(p/'fresh-publication.json').write_text(json.dumps(result,indent=2));receipt=json.loads(store.get('operations/conferences/publication-receipts/'+entry['window_id']+'.json').body);assert receipt['status']=='verified';(p/'fresh-verification-receipt.json').write_text(json.dumps(receipt,indent=2));print('Fresh DOI window verified',entry['window_id'],flush=True)
