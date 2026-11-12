# UK MHRA — November 10, 2026

Entry 20 (`uk_mhra`) is reviewed after original evidence, replay and Athena checks. `japan_pmda` is a different source. No new credential or owner account action is required.

## Root cause and repair

The old metadata contract had an empty host allowlist and no source-specific structured-attachment validator. Saved designation registers therefore failed `missing_verified_raw_artifacts:provider_record` and tripped the source circuit breaker.

New immutable contract 2.0.3 and `metadata_engine/mhra.py` verify official CSV/XLSX attachment origin, checksum, entire row equality and composite identity. Current/expired assertions remain distinct. A legacy expired row without a `registerStatus` may retain its original unqualified `orphan:` ID; the verified artifact explicitly identifies the expired register. No raw IDs are rewritten and no expired source is inferred current. Holder enrichment is separate and is not promoted to a verified legal-company match.

All four saved failed batch slices validated (32 + 32 + 5 + 32 rows). Requeued/superseded **51 unfinished jobs**, retaining original data/failure evidence. Three selected legacy job replays and a new product-document replay passed. Reviewed-source date queues are installed locally, remotely and in installer defaults; remaining queued work continues without source-wide stopping for an individual gap.

## Broader all-medicine capture

The original route covered **ILAP/current/expired orphan-designation lists only**, not every medicine. Added `mhra_products_worker.py` and **`optima-mhra-products.timer`** to traverse the whole public MHRA product-information search catalogue with `search=*` and no company, product, active-substance or document-type filter.

MHRA describes its public service as providing SPCs, PILs and PARs: [official catalogue](https://products.mhra.gov.uk/) and [official guidance](https://www.gov.uk/guidance/find-product-information-about-medicines).

Live probes found **79,646 document entries** overall, later **79,648** as the feed changed; an initial SPC-only diagnostic counted 24,837. These are **document counts, not unique drugs or a complete current licence inventory**. The collector uses the whole catalogue, not the diagnostic SPC filter.

Each successful document capture saves:

- the complete original catalogue response/record and provider URL;
- original PDF bytes, SHA-256 and extraction provenance;
- complete extracted text, or explicit `no_extractable_text` for an image-only PDF;
- a committed native `uk_mhra/research_records` manifest.

Metadata validates both the exact original catalogue row/link and original PDF bytes/text. Index-only entries cannot pass as complete medicine documents. Document identity is tied to the official document URL; it is not an inferred unique medicine or legal-authorisation identity.

The service continues **120 seconds after completion**, up to ten entries per invocation, 384 MiB memory, 20% CPU and a five-minute service timeout. Per-document processing is bounded to 45 seconds; a run stops taking new entries after 170 seconds. Exceptions/timeouts are saved as individual gaps and the following documents proceed. The worker does not use the controller's shared RAM/capture locks. No IAM expansion was required. Systemd units are persisted in the repository's `systemd/` directory.

Provider discovery uses the official site's publicly supplied read-only query configuration; no query key is hardcoded or included in saved evidence URLs. Original PDFs are restricted to the official MHRA blob document host.

Verified checkpoints: **10 completed documents / zero gaps initially; 20 completed attempts / zero gaps at the final saved checkpoint**, offset 20 and provider count 79,648. Whole-catalogue capture remains **incomplete**. Counts can change while the rolling harvest runs, and offset enumeration is not a point-in-time snapshot or proof of exhaustive unique-drug coverage. Repeated document tasks reuse committed captures; publication/metadata backlog remains visible. The collector stops explicitly if a future catalogue reaches the provider's 100,000-offset boundary rather than claiming completion beyond it.

State: `research-data/constellation-backfill/specialist-schedulers/mhra-products/state.json`. Per-file gaps and cycle receipts are under `research-data/constellation-backfill/legacy-operation-receipts/mhra-products/`. Successful complete heads enter the existing regulatory publication discovery route; private worker queue receipts retain evidence.

## Athena verification

Aggregate **`24ec3092-38b7-483d-a2eb-6feb888be547`** returned **70 raw-complete observations / four raw batches**, latest ingestion November 10, 12:01:10 UTC. Counts will grow as processing continues.

Metadata payload query **`0c7d8d98-1aeb-41df-ac6b-e0cb549f3d29`** and curated regulatory query **`e84f02ed-5f00-47ab-914c-dbf5f6d42d5f`** both returned the new `medicine_document` and its **29,641-character** text. Its original PDF and original catalogue response both passed metadata validation. Canonical curated publication receipt is in `fresh-publication.json`.

Use us-east-1, AwsDataCatalog, workgroup optima-collected-data, result reuse off:

```sql
SELECT source_key, count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations"
WHERE source_key = 'uk_mhra'
GROUP BY source_key;
```

Inspect the verified full document and catalogue fields:

```sql
SELECT *
FROM optima_regulatory_pilot.research_records_windows
WHERE source = 'uk_mhra'
  AND window_id = 'a4c04081f47245a67f35413500d2ee86ce18c804841645c01f10a31b4089c415'
LIMIT 20;
```

The `data_json` column contains `catalogue_record`, `document_sha256`, `text` and `text_status`. Existing designation snapshots have `category=orphan/ilap` and are not interchangeable with medicine-document records.

## Health, tests and remaining limits

All **15 standard collection workers** were active. Metadata worker/controller and daily collection, regulatory publication and historical dispatch schedules were checked online; daily/historical collection controls permit work. The new document worker completed successfully and its timer continues. Other sources' validation holds and owner pauses remain. The unrelated controller code-backup service remains failed.

**43 focused tests passed**: exact register rows, original catalogue/PDF requirements, legacy/expired distinctions, checksum/identity/origin rejection, simulated per-file failure followed by successful capture, and metadata/enrichment regressions. Edited modules compile.

This review does not certify finished catalogue/history capture, current licence status, complete UK authorisation coverage or historical snapshots. Undated designation rows cannot establish past designation dates; older historical windows remain explicit gaps rather than invented history. Image-only PDFs may require OCR before downstream text use. Constellation product-entity registration is a separate dependency from raw document capture.

## Evidence

`before.json`, `failed-batch-validation.json`, `metadata-deployment-result.json`, `migration.json`, replay receipts, `products-state.json`, `products-state-final.json`, `fresh-capture.json`, `fresh-publication.json`, `athena-verification.json`, `metadata_sample.json`, `curated_payload.json`, `worker-health-final.json`, `collection-controls.json`, `final-status.json`, `tests.log`.

## Additional monitor failure found in the final controller check

`constellation-gap-audit.service` was OOM-killed at its 512 MiB limit in the 11:30 and 12:00 UTC runs. Its timer is enabled. Collection workers and metadata processing continue; the latest gap audit must not be described as healthy/current. The code batches SQL reads but then accumulates all jobs, report bodies and manifests in memory. Separate engineering repair is needed to stream/reduce attempted scopes and bound receipt caches, followed by a successful audit/readback. No failed flag was cleared and no audit success was invented. This monitor issue is separate from the repaired MHRA data path.
