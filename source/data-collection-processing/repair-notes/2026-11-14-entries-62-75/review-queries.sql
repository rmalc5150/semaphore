-- 62 sam_gov_opportunities; specialist_inputs
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'sam_gov_opportunities' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;

-- 63 uspto_odp; patent_office_actions
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'uspto_odp' AND dataset = 'patent_office_actions' GROUP BY source_key, dataset;

-- 64 uspto_odp; patent_petition_decisions
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'uspto_odp' AND dataset = 'patent_petition_decisions' GROUP BY source_key, dataset;

-- 65 bis_sdmx_api; public_documents
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'bis_sdmx_api' AND dataset = 'public_documents' GROUP BY source_key, dataset;

-- 66 fred_alfred_series_and_vintages; specialist_inputs
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'fred_alfred_series_and_vintages' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;

-- 67 unido_iip_and_indstat; specialist_inputs
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'unido_iip_and_indstat' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;

-- 68 ilostat_labor_statistics; public_documents
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'ilostat_labor_statistics' AND dataset = 'public_documents' GROUP BY source_key, dataset;

-- 69 imf_portwatch_shipping_activity; specialist_inputs
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'imf_portwatch_shipping_activity' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;

-- 70 ember_electricity_demand_and_generation; specialist_inputs
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'ember_electricity_demand_and_generation' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;

-- 71 wto_timeseries_api; specialist_inputs
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'wto_timeseries_api' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;

-- 72 wto_quantitative_restrictions_api; specialist_inputs
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'wto_quantitative_restrictions_api' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;

-- 73 wto_eping_sps_tbt_notifications; specialist_inputs
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'wto_eping_sps_tbt_notifications' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;

-- 74 epo_ops_patent_legal_events; specialist_inputs
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'epo_ops_patent_legal_events' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;

-- 75 copernicus_era5_era5_land; specialist_inputs
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'copernicus_era5_era5_land' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;

