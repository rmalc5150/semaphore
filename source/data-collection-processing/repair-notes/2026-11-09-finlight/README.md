# Finlight capture, metadata and Athena repair — November 9, 2026

## Verified results

The owner's metadata query now returns **160 observations, all raw-complete, linked to five raw batches**, including November 9 ingestion. Query `a6756902-682c-4c43-9ad8-3d395205e8d3`.

Curated news was separately verified and refreshed by publishing the complete November 3 canonical query set: eight sector/language manifests, exhausted and committed. The table now contains **13,740 distinct Finlight articles**, latest ingestion November 9. Query `b0b7aafb-ae73-4f63-90bf-e395dabf88c1`. The older published baseline was 12,721 articles and October 22 ingestion.

Finlight is marked reviewed in the verification schedule after these checks. This review covers available source records and working publication, not full history, entity matching, historical availability vintages or universal publisher full text.

## Root causes and repairs

- Source contract `2.0.2` had an empty allowed-host list, rejecting actual saved Finlight responses. Generic JSON rules were also unsuitable for a news-provider record.
- Added `metadata_engine/finlight.py`: accepts only original API article responses from the exact Finlight endpoint; checks unique article identity, URL, title, publication timestamp, source, language and supplied provider fields against the collected record. Request-parameter receipts and wrong/duplicate/mismatched articles fail.
- Contract `2.0.3` explicitly scopes completeness to the provider article record. This does not substitute summaries for publisher full text. Publisher captures remain linked in payloads.
- Preserved failed reports and superseded/requeued 235 old-contract jobs. Four previously failed batch slices plus a current-day batch passed production processing; 160 observations published through staged Athena count checks. Remaining slices/input jobs continue normally.
- Applied reviewed-source `queue_by_source_date` handling in root/worker configuration and installer defaults. Source remains enabled with zero consecutive raw failures.
- Added Finlight policy generation to runtime source policies; deployed validator/evidence/policy modules on the metadata worker. Focused tests cover request-only, identity/content mismatch and duplicate/wrong-host rejection.

## Capture and historical scheduling

Current-day raw API responses were already saved (including 14:08 UTC), proving the collector had not stopped with metadata processing. Capture/publication timers are enabled.

The finite archive cursor was incorrectly configured for 2016 despite an observed archive boundary of January 2021. Corrected its start to January 1, 2021; preserved the earlier configuration as evidence. The 2016–2020 period remains unverified, not declared permanently unavailable. Archive target ends October 11 exclusive; daily/reconciliation handles later dates.

Enabled `optima-news-collection-historical.service` in the legacy historical dispatcher. Updated its executor registry as well as workspace registries. Its normal command is `news_operations.py --lane historical`, retaining provider budgets (1,000/day, 100/archive invocation), checkpointing, source locks and canonical publication queues.

The worker could not read `newKeys`. Mirrored only `finlight-api-key` into its already-authorized `dataSourceAPIkeys` secret, preserving all other values and recording version IDs without storing keys in reports. Only the historical workspace's daily-config secret reference changed. Future Finlight key rotations must keep this mirror synchronized. The temporary direct `newKeys` GetSecretValue grant was neutralized; this instance cannot delete inline policies, so it now grants no key-value read permission. Existing source bundle access is used instead.

Three earlier attempts failed on executor registry, credentials and full-text cache permissions; their reports are retained. Added only GetObject/PutObject for `operations/news/fulltext/{content,publisher-budgets}/*`, with no deletion rights. A new audited invocation `7281d035a7689b936a38478ea7d6bfe2b6b60c9c9bf6a5b9632c0368b2b07232` is running under normal leases, CPU/memory bounds and provider limits. The existing archive checkpoint resumed at **November 10, 2021**, retaining earlier progress rather than restarting at January 1. See `historical-job-after.json` and `archive-live-evidence.json`.

At 16:37 UTC the source API budget advanced to 198/1,000 requests, and the publisher budget to 812/1,000, with newly written article-cache receipts. One inspected historical publisher cache is explicitly `unavailable`, not full text; source/API metadata remains captured. Daily caps and unavailable/pending full-text states are retained. A running invocation is not full historical completion.

## Useful SQL

```sql
SELECT source_key, count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM optima_metadata_engine.source_observations
WHERE source_key = 'finlight'
GROUP BY source_key;
```

```sql
SELECT source, count(*) AS row_occurrences,
       count(DISTINCT record_id) AS distinct_articles,
       max(last_observed_at) AS latest_ingestion
FROM optima_news_research.news_articles_windows
WHERE source = 'finlight'
GROUP BY source;
```

Metadata completeness is provider-record completeness. Source query exhaustion, publisher full text, confirmed entity links and historical point-in-time suitability are independent assertions.

No new owner credentials/purchase are needed. Keep historical completion and the existing receipt-verified plan-downgrade notice open until capture, publisher-content and publication checks finish.

## Evidence

`failed-jobs-before.json`, `failed-batch-validation.json`, `jobs-before-migration.json`, `migration.json`, deployment/replay results, `athena-verification.json`, `curated-publication.json`, `curated-athena-after.json`, `review-policy-result.json`, `historical-dispatch.json`, archive logs, credential-wiring version metadata and `tests.log`.
