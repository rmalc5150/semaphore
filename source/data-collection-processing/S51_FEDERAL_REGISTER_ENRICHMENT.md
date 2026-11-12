# S51 full-notice and chemical/use enrichment

Deployed October 18, 2026. Metadata discovery remains `federal_register`. Daily enrichment now archives full notice XML (or HTML fallback), the official published PDF, and a versioned extraction artifact. The original search metadata is preserved. Chemical identities and product applicability remain unreviewed.

## Running jobs

- `specialist_inputs.py` discovers full-notice jobs after committed S51 metadata pages. Original parent observation identity and enrichment version are retained. Jobs are isolated under `operations/federal-register/discovered-jobs/`.
- `federal_register_daily.py` seeds previously captured daily metadata from today's receipts and resumes newly discovered daily/historical notices. `optima-federal-register-daily-enrichment.timer` runs every five minutes after completion, with eight notices per invocation. It uses a dedicated lightweight lane, separate from the shared heavy metadata queue. Its outputs use source `federal_register_documents`, dataset `specialist_inputs`.
- `federal_register_enrichment_backfill.py` replays the [pinned 83-batch archive](reports/federal-register-enrichment-backfill-2026-10-18/input-batches.json). The 1,161 observations represent 1,009 unique document numbers at launch. Repeated topic-search observations are grouped, preserving their count and latest parent lineage. Original IDs, publication dates and metadata are retained; enrichment is appended to `payload.data.enrichment` in source `federal_register`.
- `optima-federal-register-enrichment-backfill.timer` resumes eight documents per invocation every five minutes after completion. Config: [backfill configuration](config/federal-register-enrichment-backfill.json). The source inventory is frozen; future metadata is handled by the daily lane rather than silently expanding backfill scope.

Services use the existing Python environment and memory/CPU limits. Retries are checkpointed. Daily missing bodies/PDFs retry twice before the next attempt retains a gap outcome; gap records explicitly distinguish failed/partial retrieval from complete evidence. Backfill retries use its configured three-attempt policy; a final failure retains the original metadata and an enrichment error rather than dropping the notice. A completed collection task means its outcome was recorded, not that every artifact was retrieved.

## Evidence and extraction

`federal_register_enrichment.py` validates API document identity, source hosts, body URLs and the XML FRDOC marker. It retrieves only the supplied full-notice body and official published PDF, not a search excerpt or public-inspection draft. XML parsers disable external entity resolution/network access. A non-PDF response is rejected. Original bytes are archived under `source_documents/federal_register_documents/<sha256>`; complete extraction JSON is archived under `source_documents/federal_register_extractions/<sha256>`.

Structured fields include:

- Document number, title, type/action and conservative policy stage. Proposed, final, withdrawn and corrected stages remain separate.
- Explicit publication/effective/comment-close dates, original dates wording, docket/RIN/CFR references where provided. Missing dates are not inferred.
- Full paragraph text with original XML paths. Each qualifying chemical section retains its CFR heading, reported name, PMN identifiers, checksum-valid CAS mentions, generic/confidential flags and source document hash.
- Section-local paragraphs for conditions/requirements, exceptions/scope limits, and quantity/time/threshold passages. These are source extracts, not an exhaustive legal interpretation. Cross-referenced CFR obligations are retained as text; referenced laws/dockets are not recursively downloaded by this implementation.
- Retrieval and extraction formats, original source references, artifact gaps, review status and an explicit unreviewed product-applicability state.

A section is not treated as a chemical provision merely because a table of contents/OMB table mentions chemical substances. PMN-linked sections remain distinct even when generic names are similar. Valid CAS numbers are reported mentions, not independently verified chemical-to-product identities. Exact confidential structures/names cannot be recovered by guessing. Non-chemical notices retain their full text and policy metadata with an explicit chemical-extraction review status, rather than invented substances.

HTML fallback preserves full paragraph text but does not claim the same section-level chemical extraction as the XML parser. Notices with no detected chemical sections require review; this is not proof that no chemicals are involved. Large extraction artifacts exceeding 3 MiB are retained externally with a content-addressed reference, rather than making an oversized shared observation. Original body/PDF retrieval uses the common bounded response limit; oversized or unavailable artifacts become explicit gaps.

## Sample verification

Document `2021-26683` has been enriched and committed. Its original published PDF was downloaded and SHA256-verified. Extraction retains 45 chemical provisions and separates publication (`2021-12-10`) from effective date (`2022-02-08`). Generic identities remain flagged. The semiconductor-wafer exception is preserved only in the sections where the source states it, not applied to all 45 chemicals. [Launch verification](reports/federal-register-enrichment-backfill-2026-10-18/launch-verification.json).

These are documents retrieved now. Historical publication dates do not prove availability of the current API fields, a reconstructed historical notice rendition, or a product watchlist at that time. The published PDF is retained for verification. This collection does not reconcile all subsequent amendments or determine currently applicable law.

## Publication, queries and completion email

Daily completed manifests join the existing specialist publication queue using valid 64-character window identities. Both lanes' committed records are independently exposed by the shared committed-data publisher in `optima_collected_data.observations`. They can appear later than capture. The SQL-checks S51 section distinguishes discovery metadata, enriched records and explicit backfill gaps.

The backfill email goes to `randall@optima-holdings.com` through the existing confirmed SNS topic. It waits for all pinned batches/documents to be processed, every output batch to be verified by the shared publisher and exact source/job counts to match an Athena query. The email discloses gaps; the complete gap receipt is retained in S3. It does not wait for RDS product matching, because chemical/material/process applicability matching is a separate, unimplemented workflow. SNS acceptance is recorded to suppress ordinary repeats; an interruption exactly between acceptance and checkpointing can repeat the notification.

## Status and downstream work

- Durable local registry: `federal-register-enrichment-backfill-2026-10-18.sqlite3`.
- Local reports: `reports/federal-register-enrichment-backfill-2026-10-18-latest.json` and `reports/federal-register-daily-enrichment-latest.json`.
- Backfill S3 state/config/inventory/receipts: `operations/federal-register/enrichment-backfill/<job-id>/`.
- Daily S3 checkpoints: `operations/federal-register/daily-enrichment-state.json`.
- Logs: `journalctl -u optima-federal-register-enrichment-backfill.service` and the daily enrichment service.

Tests cover the real notice, correct section-specific exceptions, confidential flags, CAS checksum validation, wrong document identity, non-chemical notices, stages, URL restrictions, idempotent daily job discovery, missing-PDF retries, preserved IDs/dates and email publication/count gating.

This implements evidence enrichment, not chemical-to-product matching or automatic business impact. The [product-population plan](ENTITY_DISCOVERY_ROLLOUT_PLAN.md) and [event plan](ENTITY_DISCOVERY_ROLLOUT_PLAN.md#event-pipeline) describe the remaining material/process evidence links and policy-event integration. A semiconductor term, generic chemical name or source publication alone must not become a restriction against every tracked chip/product.
