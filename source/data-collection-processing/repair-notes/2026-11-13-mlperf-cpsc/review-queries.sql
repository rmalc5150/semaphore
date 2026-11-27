-- us-east-1; AwsDataCatalog; workgroup optima-collected-data; result reuse off.
SELECT source_key, count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM optima_metadata_engine.source_observations
WHERE source_key IN ('mlperf_results', 'cpsc_recalls')
GROUP BY source_key;

-- Published benchmark rows; file inventories and supporting logs are separate kinds.
SELECT source_record_id, ingested_at,
       json_extract_scalar(labelled_json, '$.payload.data.repository') AS repository,
       json_extract_scalar(labelled_json, '$.payload.data.commit') AS commit_sha,
       json_extract_scalar(labelled_json, '$.payload.data.result.Model') AS model,
       json_extract_scalar(labelled_json, '$.payload.data.result.Scenario') AS scenario,
       coalesce(json_extract_scalar(labelled_json, '$.payload.data.result.Performance_Result'),
                json_extract_scalar(labelled_json, '$.payload.data.result.Result')) AS provider_result,
       coalesce(json_extract_scalar(labelled_json, '$.payload.data.result.Performance_Units'),
                json_extract_scalar(labelled_json, '$.payload.data.result.Units')) AS provider_units,
       json_extract(labelled_json, '$.payload.data') AS full_provider_data
FROM optima_metadata_engine.source_observations
WHERE source_key = 'mlperf_results' AND record_kind = 'benchmark_result'
LIMIT 25;

SELECT source_record_id, ingested_at,
       json_extract_scalar(labelled_json, '$.payload.data.Title') AS title,
       json_extract_scalar(labelled_json, '$.payload.data.RecallDate') AS recall_date,
       json_extract(labelled_json, '$.payload.data.Products') AS products,
       json_extract(labelled_json, '$.payload.data.Hazards') AS hazards,
       json_extract(labelled_json, '$.payload.data.Remedies') AS remedies,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key = 'cpsc_recalls'
ORDER BY ingested_at DESC
LIMIT 25;
