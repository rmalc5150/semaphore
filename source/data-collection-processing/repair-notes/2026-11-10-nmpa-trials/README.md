# NMPA trials — reviewed November 10, 2026

The SQL was empty because metadata validation stopped after four generic HTML-evidence failures. There was also a collection scheduling defect: the old inventory timers were disabled and the detail-enrichment migration route was disabled. A public discovery crawler remained active, but it was not a replacement for those producers.

## Fixed and verified

- Added dataset-specific original-page validation. **Inventory rows** must match their registration ID, every saved listing column, page number and advertised totals. They are labelled `record_kind = 'registry_inventory'`, `completeness_scope = 'original_registry_inventory_row'` and flagged `registry_inventory_not_trial_detail`.
- **Full trial records** require the matching original detail page, complete parsed field list and matching structured facts. Drug names, sponsors, phase, sites, enrolment, endpoints and explicit dates retain their source values. Missing provider dates remain unknown; no date is invented.
- **Events** retain their distinctions: explicit milestones must match the original source fact; first-observed events describe collection observations; observed-change events require supporting before/after source values and an observation interval. They do not establish an actual clinical change date or trial success.
- Shared the existing NMPA field/fact parser between capture and validation. Registered contract **2.0.3**, requeued **23 unfinished jobs**, and successfully replayed the **80 inventory rows in all four originally failed batches**. Per-source date queues isolate later bad scopes.
- Restored substantive capture on the collection **worker**, preserving the verified original **6,359 completed trials** and the existing pending/retry queue. The original seed contained 22,495 outstanding trials; it is not discarded or reset. Current producer progress/outcomes are checkpointed separately in S3.
- Verified both historical-pending and newly discovered 2026 trials through original rendered HTML → raw records → metadata → regulatory Athena publication. The two verified sample groups contain **eight full trial snapshots and 25 events**. Sampled current trial records retain **55–71 original fields**, plus structured facts.
- **79 focused tests passed**, including original-page/identity validation, inventory/detail separation, milestones, unknown dates, source pagination, resumability, retry isolation, daily discovery despite a historical-page failure, shared request budgets, incremental verified-ID caching and publication.

## Athena results

The user's query now returns **153 raw-complete observations across 14 linked raw batches**, at query `87886745-0c96-401b-ae66-80d8889aec94`. This is a verified snapshot of processing progress, not the whole backfill or a count of unique trials.

| Dataset/type | Verified metadata observations |
| --- | ---: |
| Inventory rows | 120 |
| Full clinical-trial snapshots | 8 |
| Source-dated/collection-observation events | 25 |

Dataset reconciliation: `f175a369-12d1-4384-902c-35eca0f27458`. Full metadata payload check: `cfb69beb-8c0a-44d8-89d8-cc7afe50a1f1`. Regulatory payload check: `b8d0c772-330b-4cbc-87a1-8756a34b6f3a`. The latest four publication windows each reconciled to one trial plus two events: `5e25f737-147f-400b-a1d1-6563fe23f87e`.

Evidence: `athena-verification.json`, `athena-breakdown.json`, `metadata_sample.json`, `curated_payload.json`, `first-captures.json`, `fresh-captures.json`, `fresh-publication.json`, `failed-batch-validation.json`, `tests.log`.

## Restored production schedules

These units run on **worker `i-06241bd1c4e91c2fc`**, not the controller. The obsolete controller timers remain disabled to prevent duplicate collection.

| Worker timer | Work per invocation | Continuation |
| --- | --- | --- |
| `optima-nmpa-resumed-inventory.timer` | One baseline page and, until ten current listing pages have been observed that UTC day, one current page | Five minutes after completion |
| `optima-nmpa-resumed-details.timer` | At most four trials; newly discovered IDs take priority over the saved historical backlog | Two minutes after completion |

Both jobs use **512 MiB, 20% CPU and a five-minute invocation limit**. Individual page/trial attempts have 90-second limits. Historical-page failures cool down independently; a failed trial gets its own retry receipt and does not stop other trials. Retry delay increases after repeated failures. Existing **8,000 reserved request slots per UTC day** are shared between the two producers, reserving four slots for each retry-capable fetch. This retains the previous configured detail budget rather than increasing it. Actual provider/account limits still apply.

The inventory resumed from **page 1,461 / 28,854 saved IDs** and was observed advancing through page 1,463. Zero newly added IDs on an old page is possible when the moving listing overlaps already captured IDs; it is not evidence of a frozen snapshot. Separate current-day listing pages produced new 2026 IDs, which were then captured by the detail worker.

A checksum-verified incremental ID cache avoids downloading every old raw inventory batch on each page continuation. It is rebuildable; refreshed manifests invalidate obsolete cache membership. Original raw data and durable outcomes remain in S3.

The original enrichment seed is read-only and SHA-256 verified. New progress, per-trial outcomes, retries and budget reservations use:

`research-data/constellation-backfill/legacy-operation-receipts/nmpa-resumed/`

Complete trial manifests enter the existing regulatory publication pipeline through an idempotent worker-queue bridge. A verified publication receipt, rather than a running timer or queued batch, establishes Athena availability. More captured records and metadata/publication jobs will continue to arrive after the sample counts above.

All 15 existing collection workers and the metadata worker were active/processing successfully at verification; NMPA is enabled with zero consecutive raw failures. Other sources' existing holds remain separate. No owner-paused source was resumed. Runtime evidence: `capture-deployment-result.json`, `inventory-head-before.json`, `inventory-head-after.json`, `resumed-progress.json`, `final-capture-status-command-result.json`, `worker-check-command-result.json`.

## Your action and scope

**No new NMPA account, key or scraping subscription is needed based on the successful live captures.** Optional: inspect the SQL samples below. The direct listing requests returned HTTP 403; the configured rendered scraping route succeeded and remains in use.

This review covers verified inventory/detail/event material and the working capture-to-Athena path. **The historical backfill, full inventory reconciliation and metadata/publication catchup are still in progress.** Daily discovery observes the first ten current listing pages, not a guaranteed exhaustive count of all new registrations if listing movement exceeds that overlap. Captures are current observed versions with source dates; they do not reconstruct historical registry vintages or all protocol attachments. Entity matches remain candidates.

Use **us-east-1 → AwsDataCatalog → optima-collected-data**, result reuse disabled:

```sql
SELECT source_key, count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations"
WHERE source_key = 'nmpa_trials'
GROUP BY source_key;
```

Separate inventory from full trial/event records:

```sql
SELECT dataset, record_kind,
       json_extract_scalar(labelled_json, '$.payload.record_type') AS record_type,
       count(*) AS observations
FROM optima_metadata_engine.source_observations
WHERE source_key = 'nmpa_trials'
GROUP BY 1, 2, 3;
```

Inspect full trial payloads, with fields at `$.payload.data.fields` and structured facts at `$.payload.data.structured`:

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'nmpa_trials'
  AND dataset = 'research_records'
  AND json_extract_scalar(labelled_json, '$.payload.record_type') = 'clinical_trial'
ORDER BY rand()
LIMIT 20;
```

The regulatory table exposes those same original fields/facts through `data_json`:

```sql
SELECT *
FROM optima_regulatory_pilot.research_records_windows
WHERE source = 'nmpa_trials'
  AND record_type = 'clinical_trial'
ORDER BY rand()
LIMIT 20;
```

A sample may return fewer than 20 rows while verified publication catches up. Inventory-only rows intentionally have a different payload shape; a missing `$.payload.data.fields` on an inventory row does not mean its full trial detail has been captured.
