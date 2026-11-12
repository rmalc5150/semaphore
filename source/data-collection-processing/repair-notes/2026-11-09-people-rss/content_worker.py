"""Repair saved RSS body gaps independently; retain unavailable articles and budgets."""
import json,hashlib,sys
sys.path.append("/opt/constellation/metadata-engine-runtime")
from datetime import datetime,timezone,timedelta
from pathlib import Path
from collection_storage import StorageSettings
from metadata_engine.runtime_db import Database,fingerprint
from people_rss_content import Capture,VERSION
from finlight_content_backfill import enrich_one
from research_contract import digest
ROOT=Path(__file__).resolve().parent
settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();config=json.loads(Path('/opt/constellation/metadata-engine-runtime/config/metadata-engine.json').read_text());db=Database(config);s=db.session.client('s3');bucket=settings.s3_bucket
with db.tx()as c:
 c.execute("SELECT f.failure_id,f.error_reason,j.input_key FROM pipeline_failures f JOIN engine_jobs j ON j.job_id=f.job_id WHERE f.source_key='people_rss' AND f.stage='rss_article_content' AND f.status='open' ORDER BY f.last_seen_at LIMIT 50");gaps=c.fetchall()
client=Capture(store,None,max_publisher_requests=4);processed=0;seen=set();cache={}
for gap in gaps:
 if processed>=2:break
 key=gap['input_key']
 if key not in cache:
  raw=s.get_object(Bucket=bucket,Key=key)['Body'].read();cache[key]=(raw,[json.loads(l)for l in raw.splitlines()])
 raw,rows=cache[key];parent=next((r for r in rows if fingerprint(['people_rss',r['source_record_id'],'rss_article_content'])==gap['failure_id']),None)
 if not parent or parent['source_url']in seen:continue
 seen.add(parent['source_url']);saved=store.get('operations/news/fulltext/people_rss/content/'+digest(parent['source_url'])+'.json')
 if saved:
  old=json.loads(saved.body)
  if old.get('version')==VERSION and old.get('status')=='unavailable' and datetime.now(timezone.utc)-datetime.fromisoformat(old['captured_at'].replace('Z','+00:00'))<timedelta(hours=6):continue
 processed+=1
 try:
  manifest=json.loads(store.get('manifests/collection_runs/source=people_rss/dataset=people_source_records/'+parent['run_id']+'/final.json').body);task=manifest['task'];universe=json.loads(store.get('manifests/configurations/universe/'+task['universe_hash']+'.json').body);taxonomy=json.loads(store.get('manifests/configurations/taxonomy/'+task['taxonomy_hash']+'.json').body);day=datetime.fromisoformat(parent['ingested_at'].replace('Z','+00:00')).date();cfg={'provider':'people_rss','dataset':'people_source_records','start':str(day),'end_exclusive':str(day+timedelta(days=1))};lineage={'batch':key.removeprefix('research-data/'),'batch_sha256':hashlib.sha256(raw).hexdigest(),'observation_id':parent['observation_id'],'record_id':parent['record_id']}
  # New code version gives a fresh task; cached success reuses immutable evidence.
  capture,manifest_key=enrich_one(store,settings,universe,taxonomy,cfg,parent,lineage,client,1);m=json.loads(store.get(manifest_key).body)
  for page in m['pages']:
   for batch in page['batches']:
    raw_key='research-data/'+batch['key'];etag=s.head_object(Bucket=bucket,Key=raw_key)['ETag'];db.enqueue('people_rss',raw_key,etag,'legacy_batch',100)
  print(json.dumps({'article':parent['source_url'],'status':capture['status'],'characters':capture.get('text_characters',0),'manifest':manifest_key}),flush=True)
 except Exception as error:print(json.dumps({'article':parent['source_url'],'status':'retry','reason':getattr(error,'code',type(error).__name__)}),flush=True)
print(json.dumps({'processed':processed,'candidate_gaps':len(gaps)}),flush=True)
