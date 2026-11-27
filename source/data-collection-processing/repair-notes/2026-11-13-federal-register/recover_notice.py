"""Append a complete capture for the notice whose old PDF exceeded 64 MiB."""
import fcntl,json
from pathlib import Path
from collection_storage import StorageSettings,now,write_json
from research_contract import ROOT,load_json,digest
from specialist_inputs import collect

settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store()
old_key='manifests/collection_runs/source=federal_register_documents/dataset=specialist_inputs/run_78cbf8bb-7953-4602-8409-3ba96e2b4daf/final.json'
old=json.loads(store.get(old_key).body);task=old['task'];scope=task['scope'];parameters=dict(scope['parameters']);parameters.pop('allow_partial',None)
assert parameters['listing']['document_number']=='2026-22743'
job={'source':'federal_register_documents','source_id':scope['source_id'],'adapter':scope['adapter'],
     'mode':task['mode'],'start':task['window']['start'][:10],'end':task['window']['end'][:10],
     'parameters':parameters,'coverage_note':scope['coverage_note']}
with Path('/opt/constellation/capture-workers/capture.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 result=collect(job,store,settings,load_json(ROOT/'config/company-universe.v0.5.json'),load_json(ROOT/'config/sectors.v1.json'),1)
 report={'at':now(),'document_number':'2026-22743','old_partial_manifest':old_key,'job':job,'result':result}
 if result['status']=='complete':
  manifest=json.loads(store.get(result['manifest']).body)
  assert manifest['status']=='complete'and manifest['record_count']==1
  batch=manifest['pages'][0]['batches'][0];record=json.loads(store.get(batch['key']).body.splitlines()[0]);e=record['payload']['data']['enrichment']
  assert e['retrieval_status']=='complete'and e['official_pdf_status']=='downloaded'
  report.update(batch_key=batch['key'],official_pdf_source=e['official_pdf_source'])
  key='operations/specialists/publication-queue/fr-recovery-'+digest(result['manifest'])+'.json'
  if store.get(key)is None:write_json(store,key,{'window_id':digest(result['manifest']),'manifests':[result['manifest']],'queued_at':now()})
 write_json(store,'constellation-backfill/repairs/federal-register-20261113/recovered-notice.json',report)
 print(json.dumps(report),flush=True)
 if result['status']!='complete':raise SystemExit(2)
