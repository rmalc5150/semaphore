"""Bounded source-specific publication keeps reviewed queues moving independently."""
import json,time
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.controller import publish
from metadata_engine.reviewed_continuation import SOURCES

# Screening originals use the isolated streaming worker, while their accepted
# outputs can share this bounded publication pass with other reviewed sources.
PUBLICATION_SOURCES=('japan_mhlw_ndb_open_data','cninfo_mainland_china_company_disclosures','china_nbs_industrial_production','china_miit_electronics_and_battery_statistics','china_nea_power_statistics','china_nhsa_reimbursement_and_procurement','china_mofcom_export_controls','south_korea_fss_opendart','taiwan_twse_mops_issuer_and_revenue_archives','taiwan_customs_trade_statistics','india_ibm_mineral_production','indonesia_esdm_and_geological_agency_mineral_statistics','brazil_anm_mineral_yearbook','brazil_anm_cfem_mining_royalties','nasa_power_weather_and_solar_resource','usgs_earthquakes','ucdp_organized_violence','arxiv','england_nhsbsa_prescribing_data','sia_wsts_public_semiconductor_sales','semi_worldwide_equipment_billings','international_federation_of_robotics_world_robotics','iea_pvps_solar_deployment_reports','germany_g_ba_drug_benefit_assessments','france_has_medicine_assessment_opinions','canada_cda_amc_cadth_reimbursement_reviews','france_assurance_maladie_open_medic','imf_portwatch_shipping_activity','unido_iip_and_indstat','wto_quantitative_restrictions_api','wto_eping_sps_tbt_notifications','epo_ops_patent_legal_events','ember_electricity_demand_and_generation',
                     'un_comtrade','doe_storage_program','doe_storage_documents',
                     'doe_storage_benchmarks','doe_storage_funding','trade_screening',
                     'sam_gov_opportunities','bis_sdmx_api','ilostat_labor_statistics',
                     'fred_alfred_series_and_vintages','wto_timeseries_api','copernicus_era5_era5_land',*SOURCES)

def main():
 db=Database(json.loads(Path('config/metadata-engine.json').read_text()));started=time.monotonic()
 sources=tuple(dict.fromkeys(PUBLICATION_SOURCES));key='reviewed-publication-rotation'
 offset=int(db.cursor(key).get('offset',0))%len(sources)
 for step in range(len(sources)):
  if time.monotonic()-started>240:break
  source=sources[(offset+step)%len(sources)]
  try:print(json.dumps({'source':source,'published_batches':publish(db,source_key=source)}),flush=True)
  except Exception as error:print(json.dumps({'source':source,'publication_error':type(error).__name__+': '+str(error)[:200]}),flush=True)
  db.save_cursor(key,{'offset':(offset+step+1)%len(sources)})
if __name__=='__main__':main()
