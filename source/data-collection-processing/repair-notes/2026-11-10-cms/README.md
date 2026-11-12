# CMS national coverage — repair and verification, 10 November 2026

Both source queries now return records. The SQL was correct: the metadata engine had stopped both sources after the generic raw-content validator rejected valid CMS JSON. Original responses existed in S3, but their records never reached metadata publication.

The source-specific validator now checks the original response checksum, official API origin, success status, document ID/version, request identity and exact preservation of the returned record. Policy listings are labelled `coverage_inventory`; documents are labelled `coverage_document` and require coverage text. Valid short decisions are accepted. The full original API wrapper and encoded HTML remain retained; readable criteria, description, revision history, benefit category and supplied dates are additionally exposed in `payload.cms_context` in metadata. Effective dates do not establish historical API vintages.

All eight original failed batches replayed successfully: 80 policy-listing observations and four documents. Requeued unfinished native batches under contract **2.0.3**. CMS documentation website receipts are retained as discovery evidence, excluded from document processing, and cannot stop the valid document route. No source files were deleted.

Verified Athena snapshot:

| Source | Metadata observations | Linked raw batches | Raw-complete observations | Latest verified ingestion (Madrid) |
| --- | ---: | ---: | ---: | --- |
| `cms_coverage` | 114 | 6 | 114 | November 10, 22:04:46 |
| `cms_coverage_documents` | 8 | 8 | 8 | November 10, 22:07:09 |

These are observation counts, including repeated document versions across capture windows, not unique-policy or archive-completion counts. Counts grow as processing continues. Uncached aggregate query: `514d9854-e769-4354-95c2-f8a2d420136c`. Original separate queries also succeeded: `e7f21629-cb3f-470f-9c90-220f8b1ccb04` and `9aff8abc-33fb-4cae-90c1-8138d2b98df1`.

Fresh provider calls saved **345 current NCD listings, two annual-update rows and four full documents**. All rows of the proof windows, including an additional historical annual window, passed raw validation: **351 inventory observations and four documents** (`fresh-batch-validation.json`). Completed proof windows have verified publication receipts in `verified-window-receipts.json`. Both native curated and metadata payloads were queried and inspected. Examples include **Blood Counts**, **PET for Perfusion of the Heart**, and **Human Chorionic Gonadotropin**, with matching document identities and actual criteria text. Query evidence: `document_metadata_sample.json` (`131f1eb5-6f36-426e-85f5-3ec57b671192`) and `document_curated_sample.json` (`ca1b5b45-8d30-4105-abc4-5e866f4634ee`).

## Continuous operation

- Worker timers `optima-cms-coverage-discover.timer` and `optima-cms-coverage-capture.timer` continue two minutes after completion. Discovery refreshes daily national inventories and traverses configured annual history from 2016. Version-specific document jobs come from those inventories; the standalone child source remains disabled because it is parent-discovered.
- Each discovery run attempts at most two parent scopes. Each document run attempts at most four documents, with per-document deadlines and separate outcomes/cooldowns. Later sources and documents continue after an individual failure.
- Daily document jobs receive a new daily retrieval window; an existing completed version does not prevent subsequent daily refresh. Historical windows and old shared discovery queues remain resumable.
- Completed captures enqueue their raw batches directly in the metadata runtime. Capture and metadata are separate installations; enqueueing uses a bounded subprocess in the metadata installation. The integration failure found during testing was repaired, with only its affected checkpoints made immediately retryable. Original failure receipts remain for audit.
- Controller timer `optima-cms-coverage-publication.timer` publishes two CMS windows per run using the same specialist publication configuration and lock as the existing publisher. This prevents inconsistent receipt hashes or overlapping specialist publication. It continues two minutes after completion.
- Metadata jobs retain normal source locking, lease fencing, bounded row continuation and publication. Both source contracts use date-specific failure handling, so a later bad record is logged without stopping the source.

All 15 historical worker services and the metadata timer were active during verification. This does not certify unrelated source contents; their independent validation failures remain visible. Owner-paused sources remain paused. **61 focused/regression tests passed**. The specialist test suite uses its checked-in example universe instead of replacing the runtime-managed missing `/dev/shm` symlink.

## Your Athena checks

Run in `AwsDataCatalog`, region **us-east-1**. These are the same source keys used by the verification schedule:

```sql
SELECT source_key,
       count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM optima_metadata_engine.source_observations
WHERE source_key IN ('cms_coverage', 'cms_coverage_documents')
GROUP BY source_key;
```

Policy listings:

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'cms_coverage'
ORDER BY rand()
LIMIT 20;
```

Full policy documents:

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'cms_coverage_documents'
ORDER BY rand()
LIMIT 20;
```

Readable coverage criteria for specialist review:

```sql
SELECT source_record_id,
       json_extract_scalar(labelled_json, '$.payload.cms_context.title') AS title,
       json_extract_scalar(labelled_json, '$.payload.cms_context.benefit_category') AS benefit_category,
       json_extract_scalar(labelled_json, '$.payload.cms_context.coverage_criteria_text') AS coverage_criteria,
       json_extract_scalar(labelled_json, '$.payload.cms_context.effective_date_as_supplied') AS effective_date,
       ingested_at,
       raw_s3_uri
FROM optima_metadata_engine.source_observations
WHERE source_key = 'cms_coverage_documents'
ORDER BY ingested_at DESC
LIMIT 20;
```

The native curated table is `optima_specialist_inputs.source_observations_windows`. Listing titles are in `payload_json` → `$.data.title`; document titles and original coverage text are in `$.data.data[0].title` and `$.data.data[0].indications_limitations`. For a bounded native document sample:

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE window_id = '485d59095597c01c0caed0fb9def767632f4ea25d6671a70add4ccde73a460e1'
  AND source = 'cms_coverage_documents'
LIMIT 20;
```

This partition contains one verified document; `LIMIT 20` is an upper bound. Random ordering on the metadata samples scans the matching source, so use bounded native windows if the source later exceeds your scan budget.

## Review scope and remaining collection

**Both sources pass review for the configured national Medicare NCD route. No new key, account or manual restart is needed from you.** Historical collection, metadata catchup and publication continue; this review does not certify completion of every NCD version. Local coverage determinations, commercial payer policies, verified company/product links, licensed coding content and past API vintages are separate coverage requirements. CMS documents the national report and NCD detail endpoints in its [official API documentation](https://api.coverage.cms.gov/docs/swagger/index.html).
