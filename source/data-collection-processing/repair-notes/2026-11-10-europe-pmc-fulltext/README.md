# Europe PMC full text — repaired and reviewed, 10 November 2026

The raw files were present, but metadata stopped after rejecting their host. The old contract allowed Europe PMC website hosts while the collector saved original full article XML from **www.ebi.ac.uk**, with an official **eutils.ncbi.nlm.nih.gov** fallback. Website-discovery receipts were also being submitted as if they were full articles.

Contract 2.0.3 permits only the specific official article API routes and retains the complete-full-text requirement. The new validator checks the original JATS XML, matching primary PMCID, checksum, source URL, article title/body and saved XML content. It preserves provider XML processing instructions. Abstracts, discovery pages, partial/altered articles and mismatched IDs cannot pass. Original documents and licence statements remain saved; rights are not inferred from API availability.

## Verified results

- The three originally failed article batches passed original-evidence validation and metadata replay.
- Seventy-one unfinished metadata jobs were requeued under the corrected contract. Confirmed discovery-only inputs are now explicitly superseded as non-article inputs, with their job history and all files retained. Future discovery receipts receive the same classification; genuine article failures remain errors.
- A live historical replay of the original **January 2021** scope captured **PMC8561610** successfully. This is a present-day retrieval of an article discovered through that scope, not proof of a 2021 API vintage.
- The original SQL now returns **14 observations, all raw-complete, across 14 raw batches**, latest verified ingestion **2026-11-10T20:21:14.759482Z**. These are observations, including repeat retrievals; they are not a unique-paper or complete-history count.
- Eleven captured article windows have verified curated publication receipts. Fresh current and historical payloads were read in both Athena tables. Representative samples retain **105,626–210,043 XML characters** and **37,923–72,032 body-text characters**, with matching titles and PMCIDs.
- Aggregate query: `882b0e2c-ab5e-4915-9edb-fbbac8131f59`. Metadata payload query: `59c70fd6-2148-42d1-bc41-fde1f8cfa162`. Specialist payload query: `46949f31-b5f8-44cc-aee9-d3c972b72e9c`.
- Source enabled, contract 2.0.3, zero consecutive raw failures. **59 focused tests passed**, covering XML/identity checks, fallback, derived-context validation, discovery classification, failure isolation, checkpoint ETags, bounded queue scans and existing collection/metadata regressions. Tests used an isolated universe fixture because the production universe is mounted only inside the runtime supervisor.

## Continuing collection

Worker `i-06241bd1c4e91c2fc` runs:

| Timer | What it does |
| --- | --- |
| `optima-epmc-fulltext-discover.timer` | Daily vaccine/gene-therapy/immunotherapy clinical-trial topic discovery with seven-day publication lookback; incremental indexing of the two original shared document queues, 50 entries from each per run. |
| `optima-epmc-fulltext-capture.timer` | Fetches original linked articles from the source-specific queue, at most four attempts/run. Current and historical jobs preserve their original scope and provenance. |

Both continue **two minutes after completion**, with 384 MiB memory, 20% CPU and a five-minute service limit. A document has a 75-second deadline and a six-hour failure cooldown; receipts distinguish its actual result from the worker finishing its bounded invocation. Queues and cursors are durable S3 state with conditional updates. Completed articles use checkpoints. A failed article does not stop attempts for other articles or other sources.

The pipeline uses `epmc_fulltext_capture.py`, the native collector and `metadata_engine/epmc_fulltext.py`. New complete records retain full XML and parsed title/body, source identifiers, dates and licence context. Twenty original saved article scopes were recovered into the dedicated queue; the historical shared queues continue to be indexed. A source-specific publication bridge passes only committed complete manifests to the existing verified Athena publisher.

The child-source configuration remains parent-discovered, rather than pretending it is a standalone all-article search. Europe PMC **metadata** is a separate source (`europe_pmc`); this review concerns `europe_pmc_fulltext`. Shared daily capture excludes the parent source now handled by the independent discovery worker; the existing historical parent route remains in place.

Latest discovery/capture runs exited successfully. Both timers, metadata processing and all 15 native/legacy/public historical workers were active during inspection; no failed worker-host systemd units remained. Unrelated source-level errors still exist and are not certified repaired here. Historical capture, metadata/publication backlog and archive completeness continue; this review does not cover all literature, unavailable articles, external supplements, images/binary attachments or historical API/document vintages.

## Your Athena check

No new credentials or manual restart are needed. In **us-east-1**, choose **AwsDataCatalog**, workgroup **optima-collected-data**, and disable result reuse.

```sql
SELECT source_key,
       count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM optima_metadata_engine.source_observations
WHERE source_key = 'europe_pmc_fulltext'
GROUP BY source_key;
```

Inspect the metadata columns and full saved payload:

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'europe_pmc_fulltext'
ORDER BY rand()
LIMIT 20;
```

Inspect specialist curated observations:

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE source = 'europe_pmc_fulltext'
ORDER BY rand()
LIMIT 20;
```

For an immediately readable article-body sample:

```sql
SELECT source_record_id,
       raw_s3_uri,
       ingested_at,
       json_extract_scalar(labelled_json, '$.payload.data.enrichment.title') AS title,
       json_extract_scalar(labelled_json, '$.payload.data.enrichment.body_text') AS article_body
FROM optima_metadata_engine.source_observations
WHERE source_key = 'europe_pmc_fulltext'
ORDER BY ingested_at DESC
LIMIT 3;
```

Metadata `labelled_json` stores article data under `payload.data`; specialist `payload_json` uses `data`. Original `article_xml` is retained in both. New captures also have `enrichment`; earlier curated records retain XML without that derived context, while metadata derives it from verified XML. Dates and rights remain source facts; no historical availability, company/product linkage or scientific-validity inference is made.

Evidence files beside this report include `before.json`, `failed-batch-validation.json`, `migration.json`, deployment/replay results, `historical-seeds.json`, `historical-probe-command-result.json`, `verified-window-receipts.json`, `athena-verification.json`, `metadata_sample.json`, `curated_payload.json`, `final-status.json`, worker-check results and `tests.log`.
