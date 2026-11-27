-- us-east-1 / AwsDataCatalog / workgroup optima-collected-data; result reuse off.
-- Counts are published observation occurrences, including repeated captures/artifact records.
SELECT source_key, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations FROM optima_metadata_engine.source_observations WHERE source_key IN ('usgs_minerals','eia_battery_generators','eia_retail_prices','caiso_prices','bls_wages','ror_institutions') GROUP BY source_key;

-- Dated review examples use immutable published job partitions to bound scans.
-- Remove the job_id filter for a wider source preview. Raw/SQL review is not full archive completion.

-- 50. USGS minerals
SELECT source_key,dataset,record_id,source_record_id,raw_completeness_status,ingested_at,json_extract(labelled_json,'$.payload.data') provider_data,json_extract(labelled_json,'$.raw_artifacts') original_evidence FROM optima_metadata_engine.source_observations WHERE source_key='usgs_minerals' AND job_id IN ('b2d0e0b01b23819c7f43fcef0d2efaaa4f93f1b794d6aff1ff40974a6b96bcbd','56016f92d77d0be239e8553b04fb5d3c24744ca8d45cc2b53c9a67b05b7cf2f3') AND dataset='specialist_inputs' AND json_extract(labelled_json,'$.payload.data') IS NOT NULL LIMIT 3;

-- 53. EIA battery generators
SELECT source_key,dataset,record_id,source_record_id,raw_completeness_status,ingested_at,json_extract(labelled_json,'$.payload.data') provider_data,json_extract(labelled_json,'$.raw_artifacts') original_evidence FROM optima_metadata_engine.source_observations WHERE source_key='eia_battery_generators' AND job_id IN ('e4cff7cdf0dc5a66975deaa3202358f0d571e8beb41794ee8d4c311f365f689d','20816f75673b3096d15d7f48a568773772fd49c7cb14ac8bf8c9c6c6b1cf764a') AND dataset='specialist_inputs' AND json_extract(labelled_json,'$.payload.data') IS NOT NULL LIMIT 3;

-- 55. EIA retail prices
SELECT source_key,dataset,record_id,source_record_id,raw_completeness_status,ingested_at,json_extract(labelled_json,'$.payload.data') provider_data,json_extract(labelled_json,'$.raw_artifacts') original_evidence FROM optima_metadata_engine.source_observations WHERE source_key='eia_retail_prices' AND job_id IN ('594883312fc1d6eca88aee5bc96721ad4f99b847b986f6a6f3749795b8c9cbb2','9a8c6651140355a6434ce767000fbde9ddec51394efff59877f9c74fbd6b92cd') AND dataset='specialist_inputs' AND json_extract(labelled_json,'$.payload.data') IS NOT NULL LIMIT 3;

-- 56. California ISO prices
SELECT source_key,dataset,record_id,source_record_id,raw_completeness_status,ingested_at,json_extract(labelled_json,'$.payload.data') provider_data,json_extract(labelled_json,'$.raw_artifacts') original_evidence FROM optima_metadata_engine.source_observations WHERE source_key='caiso_prices' AND job_id IN ('4423be3fc1bff110e1520f9e9fbd01e82e36164ac62e190dd94e1f86233ce97e','d654ff942ad1ea3abf56bbb38d8efd5b3f46bce13752701a2b87208399e746fd') AND dataset='specialist_inputs' AND json_extract(labelled_json,'$.payload.data') IS NOT NULL LIMIT 3;

-- 57. BLS wages
SELECT source_key,dataset,record_id,source_record_id,raw_completeness_status,ingested_at,json_extract(labelled_json,'$.payload.data') provider_data,json_extract(labelled_json,'$.raw_artifacts') original_evidence FROM optima_metadata_engine.source_observations WHERE source_key='bls_wages' AND job_id IN ('4428439c0134d303dfbc47368e1239090e2a8dd14c3ac6b52eeb7a26c3f6eee2','6f63460910324e9f9afda7ab6bf0fffbd0ab5f3beeb1b765bbfe63e4858d6218') AND dataset='specialist_inputs' AND json_extract(labelled_json,'$.payload.data') IS NOT NULL LIMIT 3;

-- 58. Research Organization Registry institutions
SELECT source_key,dataset,record_id,source_record_id,raw_completeness_status,ingested_at,json_extract(labelled_json,'$.payload.data') provider_data,json_extract(labelled_json,'$.raw_artifacts') original_evidence FROM optima_metadata_engine.source_observations WHERE source_key='ror_institutions' AND job_id IN ('58a26eb38b562f6b04df357a49058a3e21686da4545f1400d09ff8e13319e8fc','79953857d5bcb9cf95bc3b8df70c6440b82e0093b8519366c7e1153f2483d0df') AND dataset='specialist_inputs' AND json_extract(labelled_json,'$.payload.data') IS NOT NULL LIMIT 3;
