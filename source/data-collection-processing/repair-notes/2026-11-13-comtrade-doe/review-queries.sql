-- us-east-1 / AwsDataCatalog / workgroup optima-collected-data; result reuse off.
-- One summary row per source; observations is the actual observation count.
SELECT source_key, count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_batches,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at
FROM optima_metadata_engine.source_observations
WHERE source_key IN ('un_comtrade', 'doe_storage_program', 'doe_storage_documents',
                     'doe_storage_benchmarks', 'doe_storage_funding')
GROUP BY source_key;

-- Complete provider rows retain quantities, units, nulls and estimation flags.
-- Scope: configured annual commodity/reporter/import-export world-total requests.
SELECT source_record_id, record_kind, ingested_at, raw_completeness_status,
       json_extract(labelled_json, '$.payload.data') AS provider_data,
       json_extract(labelled_json, '$.payload.scope') AS collection_scope,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key = 'un_comtrade'
LIMIT 25;

-- Program pages, documents, technical statements and funding statements stay
-- separate. Text is not a certified measurement, award allocation or payment.
-- Full saved extractions/tables are linked in payload.extraction_reference.
SELECT source_key, record_kind, source_record_id, ingested_at, raw_completeness_status,
       json_extract(labelled_json, '$.payload.data') AS document_or_source_statements,
       json_extract(labelled_json, '$.payload.extraction_reference') AS saved_extraction,
       json_extract(labelled_json, '$.quality_flags') AS limitations,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key IN ('doe_storage_program', 'doe_storage_documents',
                     'doe_storage_benchmarks', 'doe_storage_funding')
LIMIT 25;
