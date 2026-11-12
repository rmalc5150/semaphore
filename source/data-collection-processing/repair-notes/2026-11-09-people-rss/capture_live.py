import json,hashlib
from pathlib import Path
from collection_storage import StorageSettings
from people_rss_content import Capture
from metadata_engine.runtime_db import Database
from finlight_content_backfill import enrich_one
p=Path(__file__).parent;settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();db=Database(json.load(open('config/metadata-engine.json')));s=db.session.client('s3');b=settings.s3_bucket
with db.tx()as c:c.execute("SELECT * FROM engine_jobs WHERE source_key='people_rss' AND state='raw_failed' LIMIT 1");job=c.fetchone()
raw=s.get_object(Bucket=b,Key=job['input_key'])['Body'].read();rows=[json.loads(l)for l in raw.splitlines()];r=rows[0];manifest_key='manifests/collection_runs/source=people_rss/dataset=people_source_records/'+r['run_id']+'/final.json';manifest=json.loads(store.get(manifest_key).body);task=manifest['task'];universe=json.loads(store.get('manifests/configurations/universe/'+task['universe_hash']+'.json').body);taxonomy=json.loads(store.get('manifests/configurations/taxonomy/'+task['taxonomy_hash']+'.json').body)
client=Capture(store,None,max_publisher_requests=6);out=[]
for parent in rows[:2]:
 lineage={'batch':job['input_key'].removeprefix('research-data/'),'batch_sha256':hashlib.sha256(raw).hexdigest(),'observation_id':parent['observation_id'],'record_id':parent['record_id']};config={'provider':'people_rss','dataset':'people_source_records','start':'2026-10-30','end_exclusive':'2026-10-31'}
 captured,key=enrich_one(store,settings,universe,taxonomy,config,parent,lineage,client,1);out.append({'url':parent['source_url'],'capture':captured,'manifest':key});(p/'live-captures.json').write_text(json.dumps(out,indent=2));print(parent['source_url'],captured['status'],captured.get('capture_basis'),captured.get('text_characters'),flush=True)
