-- us-east-1 / AwsDataCatalog / workgroup optima-collected-data.
-- Turn result reuse off when checking newly published data.
-- This summary intentionally returns one row; observations is the row count.
SELECT source_key, count(*) AS observations,
       count_if(json_extract_scalar(labelled_json, '$.payload.data.name') IS NOT NULL) AS named_screening_observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM optima_metadata_engine.source_observations
WHERE source_key = 'trade_screening'
GROUP BY source_key;

-- Individual provider records. Excludes the older archive-only receipt.
-- These are observation occurrences, not a deduplicated list of people/entities.
SELECT source_key, source_record_id, record_kind, ingested_at,
       raw_completeness_status,
       json_extract_scalar(labelled_json, '$.payload.data.id') AS provider_id,
       json_extract_scalar(labelled_json, '$.payload.data.name') AS name,
       json_extract_scalar(labelled_json, '$.payload.data.source') AS provider_list,
       json_extract(labelled_json, '$.payload.data') AS provider_data,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key = 'trade_screening'
  AND json_extract_scalar(labelled_json, '$.payload.data.name') IS NOT NULL
LIMIT 25;
