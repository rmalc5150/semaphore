"""Bounded source-specific publication keeps reviewed queues moving independently."""
import json,time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import local
from metadata_engine.runtime_db import Database
from metadata_engine.controller import daily_publication_candidate, publication_candidates, publish
from metadata_engine.reviewed_continuation import SOURCES
from trade_mining_sources import SOURCES as TRADE_MINING_SOURCES

# Screening originals use the isolated streaming worker, while their accepted
# outputs can share this bounded publication pass with other reviewed sources.
PUBLICATION_SOURCES=('openalex_scholarly_graph','crossref_proceedings','eodhd',
                     'japan_mhlw_ndb_open_data','cninfo_mainland_china_company_disclosures','china_nbs_industrial_production','china_miit_electronics_and_battery_statistics','china_nea_power_statistics','china_nhsa_reimbursement_and_procurement','china_mofcom_export_controls','south_korea_fss_opendart','taiwan_twse_mops_issuer_and_revenue_archives','taiwan_customs_trade_statistics','india_ibm_mineral_production','indonesia_esdm_and_geological_agency_mineral_statistics','brazil_anm_mineral_yearbook','brazil_anm_cfem_mining_royalties','nasa_power_weather_and_solar_resource','usgs_earthquakes','ucdp_organized_violence','arxiv','england_nhsbsa_prescribing_data','sia_wsts_public_semiconductor_sales','semi_worldwide_equipment_billings','international_federation_of_robotics_world_robotics','iea_pvps_solar_deployment_reports','germany_g_ba_drug_benefit_assessments','france_has_medicine_assessment_opinions','canada_cda_amc_cadth_reimbursement_reviews','france_assurance_maladie_open_medic','imf_portwatch_shipping_activity','unido_iip_and_indstat','wto_quantitative_restrictions_api','wto_eping_sps_tbt_notifications','epo_ops_patent_legal_events','ember_electricity_demand_and_generation',
                     'un_comtrade','doe_storage_program','doe_storage_documents',
                     'doe_storage_benchmarks','doe_storage_funding','trade_screening',
                     'sam_gov_opportunities','bis_sdmx_api','ilostat_labor_statistics',
                     'fred_alfred_series_and_vintages','wto_timeseries_api','copernicus_era5_era5_land',*SOURCES)


def publication_order(db, sources, target, *, daily=False, served=None):
 ready=[]
 scan_only=deque()
 served=served or {}
 recent=time.time()-600
 for source in sources:
  try:
   _, candidates, matches=publication_candidates(db,source,target,daily=daily)
  except Exception as error:
   print(json.dumps({'source':source,'publication_error':type(error).__name__+': '+str(error)[:200],
                     'stage':'scheduling','lane':'daily' if daily else 'backlog'}),flush=True)
   continue
  pending=[row for row in candidates if row['job_id'] in matches and
           (not daily or daily_publication_candidate(matches[row['job_id']]))]
  if pending:
   # Full batches are grouped together, with the oldest accepted work first.
   # The cursor is never moved by the preview.
   ready.append((served.get(source,0)>recent,-(len(pending)//target),pending[0]['finished_at'],-len(pending),source))
  elif candidates:
   scan_only.append(source)
 return deque(item[-1] for item in sorted(ready)),scan_only


def take_source(queues, assigned):
 for queue in queues:
  for _ in range(len(queue)):
   source=queue.popleft()
   if source not in assigned:
    return source
   queue.append(source)
 return None


def scheduled_publish(db, sources):
 with db.tx() as cursor:
  cursor.execute("SELECT source_key FROM engine_sources WHERE state='enabled'")
  enabled={row['source_key'] for row in cursor.fetchall()}
 sources=[source for source in sources if source in enabled]
 if not sources:return
 key='reviewed-publication-backlog-schedule'
 state=db.cursor(key)
 offset=int(state.get('offset',0))%len(sources)
 served={source:state.get('served',{}).get(source,0) for source in sources}
 sources=sources[offset:]+sources[:offset]
 target=db.config['publication_batch_size']
 started=time.monotonic()
 # Preview at most 64 candidates per source. The release still selects up to
 # 100 jobs under the existing source lock and can scan farther if needed.
 probe=min(target,16)
 backlog,cold=publication_order(db,sources,probe,served=served)
 daily,daily_cold=publication_order(db,sources,probe,daily=True)
 print(json.dumps({'publication_plan':'ready','seconds':round(time.monotonic()-started,3),
                   'ready_sources':len(backlog),'daily_sources':len(daily)}),flush=True)
 worker=local()

 def release(assignment):
  source,lane=assignment
  began=time.time()
  try:
   if not hasattr(worker,'db'):
    worker.db=Database(db.config.copy())
   n=publish(worker.db,source_key=source,daily=lane=='daily')
   print(json.dumps({'source':source,'lane':lane,'published_batches':n,
                     'started_at_epoch':began,'elapsed_seconds':round(time.time()-began,3)}),flush=True)
   return n
  except Exception as error:
   print(json.dumps({'source':source,'lane':lane,
                     'publication_error':type(error).__name__+': '+str(error)[:200]}),flush=True)
   return 0

 gate=Path('/opt/constellation/batch-paused')
 with ThreadPoolExecutor(max_workers=2) as workers:
  wave=0
  while not gate.exists() and time.monotonic()-started<240:
   assignments=[]
   assigned=set()
   for slot in range(2):
    source=None
    lane='backlog'
    # Reserve one in four starts for daily results, with work-conserving fallback.
    if slot==0 and wave%2==0:
     source=take_source((daily,daily_cold) if wave%4==0 else (daily,),assigned)
     if source:lane='daily'
    if source is None:
     queues=(cold,backlog) if slot==1 and wave%4==1 else (backlog,cold)
     source=take_source(queues,assigned)
    if source:
     assigned.add(source)
     assignments.append((source,lane))
   if not assignments:break
   for (source,lane), count in zip(assignments,workers.map(release,assignments)):
    if count and lane=='backlog':served[source]=time.time()
    if count==target:
     # Repeat full batches after other ready sources get their turn.
     (daily if lane=='daily' else backlog).append(source)
   wave+=1
 db.save_cursor(key,{'offset':(offset+max(1,wave))%len(sources),'served':served})


def main():
 db=Database(json.loads(Path('config/metadata-engine.json').read_text()));started=time.monotonic()
 sources=tuple(dict.fromkeys((*PUBLICATION_SOURCES,*sorted(TRADE_MINING_SOURCES),'us_census_international_trade_api')));key='reviewed-publication-rotation'
 if db.config.get('publication_parallel_sources')==2:
  return scheduled_publish(db,sources)
 offset=int(db.cursor(key).get('offset',0))%len(sources)
 for step in range(len(sources)):
  if time.monotonic()-started>240:break
  source=sources[(offset+step)%len(sources)]
  try:print(json.dumps({'source':source,'published_batches':publish(db,source_key=source)}),flush=True)
  except Exception as error:print(json.dumps({'source':source,'publication_error':type(error).__name__+': '+str(error)[:200]}),flush=True)
  db.save_cursor(key,{'offset':(offset+step+1)%len(sources)})
if __name__=='__main__':main()
