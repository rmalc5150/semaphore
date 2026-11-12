# PubMed abstracts — repaired and reviewed, 10 November 2026

The query was empty because metadata processing had stopped after four `missing_verified_raw_artifacts:full_text` failures. That requirement was incorrect for the configured citation/abstract source. Raw capture existed, but the metadata gate prevented Athena publication.

Contract 2.0.3 verifies the whole matching original citation from the official NCBI EFetch XML, its primary PMID, checksum, source URL and derived context. It rejects altered/partial citations and mismatched IDs. Original XML remains saved; legacy records receive title, abstract sections, authors, dates and other source-derived enrichment. Provider records without an abstract carry an explicit quality flag. Full article access and rights are separate; the repair does not classify abstracts as articles or grant training rights.

## Verified results

- All four original failed batches replayed: 117 observations. Ten unfinished jobs requeued under the corrected contract.
- A live ESearch/EFetch request for PMID 35129803 saved and published a fresh complete citation.
- Three real daily searches completed: vaccine clinical trials **14**, gene therapy clinical trials **29**, immunotherapy clinical trials **18** observations. All three windows have verified curated publication receipts in `daily-publication.json`.
- The user's metadata aggregate returns **179 observations, all raw-complete, across eight raw batches**. Observations can overlap across topics/runs; these counts are not unique papers or archive completeness.
- Latest verified ingestion: **2026-11-10T20:03:30.173689Z**. Source enabled, contract 2.0.3, zero consecutive raw failures.
- Aggregate query: `4af823fd-99ad-42e1-8783-3618bdff2408`. Actual payload readback queries: metadata `4c3804ac-8141-42b8-8752-548edc5d996c`; specialist curated `c77edcf2-5e6c-48d5-9d3e-399870f6f43a`. Fresh samples contain matching title, original citation XML and populated abstract sections in both tables.
- **52 focused tests passed**, including complete-XML identity validation, missing abstracts, legacy enrichment, unchanged full-text rules for other sources, publication bridging, and failure isolation between daily topics.

## Continuing capture and processing

Worker `i-06241bd1c4e91c2fc` runs `optima-pubmed-daily.timer` at **08:10 Europe/Madrid**, with hourly continuation after completion. Each run uses the three configured research topics and a rolling seven-day publication-date filter. It saves at most two pages per topic per run, with a 384 MiB memory cap, 20% CPU quota and five-minute runtime limit. Completed scopes use existing checkpoints; incomplete topics continue. Errors receive durable per-topic receipts and cannot stop attempts for the other topics.

The new producer uses `pubmed_daily_capture.py`. Its complete windows enter the dedicated S3 publication queue under `constellation-backfill/specialist-publication-queue/pubmed-daily/`; `specialist_publication.py` bridges them into the normal verified publication queue. The shared capture plan assigns PubMed its own execution lane. Existing metadata discovery, validation and publication schedules remain active. The first daily run and an idempotent replay succeeded.

Historical route `constellation-specialist-pubmed_abstracts.service` remains enabled. Its saved report says the configured work through **October 26** drained; coverage is explicitly **not audited**. This review establishes the working citation/abstract pipeline and verified samples, not all PubMed coverage, complete historical publication, point-in-time vintages or reconciliation of every intervening date gap.

All 15 historical/native/legacy/public worker services were active and the worker had no failed systemd units during inspection. The metadata engine was accepting records from other sources. Some unrelated sources still have missing-object or discovery-page validation failures; this report does not certify them repaired. Controller publication and metadata timers are active, although shared publication can wait for the supervisor lock. This repair's batches were published individually and verified directly.

## Your Athena check

No new credentials or manual restart are required. In **us-east-1**, choose **AwsDataCatalog** and workgroup **optima-collected-data**, and turn off result reuse. Run:

```sql
SELECT source_key,
       count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM optima_metadata_engine.source_observations
WHERE source_key = 'pubmed_abstracts'
GROUP BY source_key;
```

For your original random-row review:

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'pubmed_abstracts'
ORDER BY rand()
LIMIT 20;
```

For specialist-ready saved payloads:

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE source = 'pubmed_abstracts'
ORDER BY rand()
LIMIT 20;
```

Inspect `labelled_json` → `payload.data.enrichment` in metadata, or `payload_json` → `data.enrichment` in curated observations. Both retain `data.article_xml`. Check title, abstract sections, PMID, authors/affiliations, publication-date precision and source links. Topic hits are candidates; these searches do not establish verified company/product linkage or scientific validity.

Evidence is saved beside this document: `failed-batch-validation.json`, `migration.json`, `athena-verification.json`, `metadata_sample.json`, `curated_payload.json`, `daily-windows.json`, `daily-publication.json`, `final-status.json`, deployment/replay results and `tests.log`. Full original raw material remains in `research-data/raw/source=pubmed_abstracts/` and `research-data/source_documents/pubmed_abstracts/` in the existing collection bucket.
