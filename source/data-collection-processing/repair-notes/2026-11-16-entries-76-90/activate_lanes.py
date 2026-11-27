from ops import *
for instance in (M7,T3):
 code=r'''import json,os,time
from pathlib import Path
roots=[Path.cwd()]if INSTANCE==T3 else [Path('/opt/constellation/metadata-engine-runtime'),Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/source'),Path('/opt/constellation/legacy/constellation-specialist-england_nhsbsa_prescribing_data.service')]
for root in roots:
 for name in ['specialist-inputs.json','constellation-specialist-historical.json']:
  p=root/'config'/name
  if not p.exists():continue
  cfg=json.loads(p.read_text())
  for row in cfg['sources']:
   if row['source']=='england_nhsbsa_prescribing_data':row['coverage_note']='All native monthly English Prescribing Data fields; current SNOMED catalogue preferred, retired catalogue retained for older releases. Bounded pages; full months require exhausted pagination. Current release selected dynamically; no patient-level records.'
  tmp=p.with_suffix('.review.tmp');tmp.write_text(json.dumps(cfg,indent=2)+'\n');os.chown(tmp,1000,1000);tmp.replace(p)
p=Path('config/constellation-legacy-routes.json')if INSTANCE==T3 else Path('/opt/constellation/config/constellation-legacy-routes.json');cfg=json.loads(p.read_text())
for row in cfg['routes']:
 if row['unit']=='constellation-public-ucdp_organized_violence.service':row['public_capture_source']='ucdp_organized_violence'
tmp=p.with_suffix('.review.tmp');tmp.write_text(json.dumps(cfg,indent=2)+'\n');os.chown(tmp,1000,1000);tmp.replace(p)
print('source plans and public lifecycle route metadata updated')
'''.replace('INSTANCE',repr(instance)).replace('T3',repr(T3))
 print(remote(instance,code)['out'])
# Restart only drained route passes; retain all pending/running/retry jobs and owner pauses.
print(remote(T3,'''import json,time
from constellation.control import Control
from constellation.historical_guard import dispatch_guard
from constellation.legacy_routes import manifest,specification
control=Control();sources=SOURCES;out=[]
with dispatch_guard(control)as acquired:
 assert acquired and control.allowed()
 for row in manifest()['routes']:
  if not row['execution_enabled']or not any(source in row['unit']for source in sources if source not in ('nice_technology_appraisals','decodo_shared_web_retrieval_access_layer','arxiv','usgs_earthquakes')):continue
  with control.db()as c:
   c.execute("SELECT job_id,status FROM backfill_jobs WHERE source_key=%s AND status IN ('pending','running','retryable_failed') LIMIT 1",('legacy:'+row['unit'],));pending=c.fetchone()
  if pending:out.append({'unit':row['unit'],'retained':pending});continue
  out.append({'unit':row['unit'],'registered':control.register(specification(row,'review-20261116-'+str(int(time.time()))))})
print(json.dumps(out,default=str))
'''.replace('SOURCES',repr(SOURCES)))['out'])
