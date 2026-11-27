-- us-east-1; AwsDataCatalog; workgroup optima-collected-data; result reuse off.
SELECT source_key, record_kind, count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_collection_batches,
       count_if(raw_completeness_status = 'complete') AS raw_complete_observations,
       min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at
FROM optima_metadata_engine.source_observations
WHERE source_key IN ('federal_register', 'federal_register_documents')
GROUP BY source_key, record_kind;

-- Listings are the complete returned search rows, not full notices.
SELECT source_record_id, ingested_at,
       json_extract_scalar(labelled_json, '$.payload.data.title') AS title,
       json_extract_scalar(labelled_json, '$.payload.data.publication_date') AS publication_date,
       json_extract_scalar(labelled_json, '$.payload.data.type') AS notice_type,
       json_extract(labelled_json, '$.payload.data') AS original_listing
FROM optima_metadata_engine.source_observations
WHERE source_key = 'federal_register'
LIMIT 25;

-- Full notices require matching metadata, original XML/HTML and official PDF.
SELECT source_record_id, ingested_at,
       json_extract_scalar(labelled_json, '$.payload.data.enrichment.title') AS title,
       json_extract_scalar(labelled_json, '$.payload.data.enrichment.policy_stage') AS reported_policy_stage,
       json_extract_scalar(labelled_json, '$.payload.data.enrichment.effective_date') AS reported_effective_date,
       json_extract_scalar(labelled_json, '$.payload.federal_register_context.full_text_characters') AS full_text_characters,
       json_extract_scalar(labelled_json, '$.payload.data.enrichment.full_text') AS notice_text,
       json_extract(labelled_json, '$.payload.data.enrichment.chemical_provisions') AS extracted_provisions,
       json_extract(labelled_json, '$.payload.data.enrichment.full_extraction_source') AS complete_extraction_artifact,
       json_extract(labelled_json, '$.raw_artifacts') AS original_metadata_body_pdf
FROM optima_metadata_engine.source_observations
WHERE source_key = 'federal_register_documents'
LIMIT 25;
