# Health Canada NOC — November 10, 2026

The missing Athena rows were a metadata-processing failure, not proof that Health Canada had no data. The source had stopped after four `missing_verified_raw_artifacts:provider_record` failures. Its original API responses were already saved.

## Repaired and verified

- Added source-specific validation against the complete original official JSON response: HTTPS origin, endpoint, query, notice/product identity and every original field. Indexes one checksummed bulk response per metadata process instead of repeatedly decoding the entire country inventory for each row.
- Registered contract 2.0.3, requeued 20 unfinished jobs and replayed all four original failed batches successfully. Enabled reviewed-source date queues so an individual bad scope does not stop this source or other pipelines.
- Captured and published the **complete current notice table: 38,276 unique NOCs**. Counts and all five product categories match the provider exactly, including 12 inactive notices. No manufacturer, company-universe, drug-type, active-status or notice-date filter limits this snapshot. Earlier annual date scopes remain enabled; this current response also retains older notices before those scopes.
- New notice snapshot service: `optima-canada-noc-daily.service`, daily **07:55 Europe/Madrid**, 384 MiB, 20% CPU, five-minute timeout. Saved original response, normalised raw rows, checksums, resumable manifest and verified curated publication all exist.
- Added a separate bounded all-NOC **drug-product capture**: `optima-canada-noc-products.service` / timer, daily calendar at **08:05 Europe/Madrid**, with boot catchup and continuation two minutes after completion. It stages the original bulk response once per UTC day, then checkpoints 4,000 rows per invocation. After a day is complete, continuation checks exit without fetching the provider again. There are **78,468 distinct product records** in the current original response; these are notice/product records, not 78,468 unique drugs.
- Fixed and tested cursor string compatibility and conditional progress-receipt updates during live product continuation. Saved failure logs are retained. A new attempt resumes committed pages, and an already-completed manifest can restore a missing progress receipt.
- **23 focused tests passed**, including original-row integrity, wrong origin/projection rejection, all-date/all-status capture, DIN integrity, real storage checkpoint/resume and conditional progress updates.

**Full product inventory completed and published:** 78,468/78,468 distinct provider records, Athena count query `f4b1aab3-e7a9-4601-8721-a503a70e4d07`. Parent reconciliation found **zero missing notice links**, query `a6e1f156-2b60-4c20-b779-e25fc27d68e5`. Random payload query `107efbc5-0e9a-448e-a336-301d18034d31` verified brand names and DIN fields. Evidence: `products-progress.json`, `products-publication.json` and `products-athena-verification.json`. Metadata labelling can remain queued after a complete snapshot has been made queryable in the curated specialist table.

## Athena verification

Use **us-east-1 → AwsDataCatalog → optima-collected-data**, with result reuse disabled.

The user's metadata query now returns rows. Initial fresh verification returned **192 raw-complete observations / six raw batches**, including today's notices and DIN/brand-name records; query `f9aec684-80da-4db1-9f21-7e7dce00381d`. These are sampled/replayed metadata batches, not the size of the full current dataset. See `athena-verification.json` for the latest count.

Full notice snapshot count query: `7dbdee16-11e1-4731-a8d6-d4737451162a`. Metadata notice payload query: `99c77fd6-ef7d-4079-8115-b9e066fcb894`. Exact category reconciliation is in `snapshot-athena-verification.json`.

```sql
SELECT source_key, count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations"
WHERE source_key = 'canada_noc'
GROUP BY source_key;
```

Inspect 20 complete notice payloads from the verified current snapshot:

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE source = 'canada_noc'
  AND window_id = '713e1e982005419394506d344f1186d37ea4de062270b1b9c5802d9dad614225'
ORDER BY rand()
LIMIT 20;
```

Inspect 20 complete product payloads from the separately verified product snapshot:

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE source = 'canada_noc'
  AND window_id = 'a2e101ca97b5c749f27ccb2db3ffb7b85846711caa7e9e6c8a980ad45019f933'
ORDER BY rand()
LIMIT 20;
```

The field `noc_crp_product_name` describes the **Canadian reference/comparator product**; it is not the authorised drug's brand name and may correctly be blank. Use `noc_br_brandname` and `noc_br_din` from the product table, joined by `noc_number`. DINs remain strings, preserving leading zeroes. Provider placeholders such as `N/A` are retained; they do not establish a known DIN. The 25,098 distinct nonempty supplied DIN values include such placeholders and are not a count of distinct approved drugs. The sentinel `noc_last_update_date = '1111-11-11'` remains preserved as original data, without being asserted as an actual update time.

```sql
SELECT source_record_id,
       json_extract_scalar(labelled_json, '$.payload.data.noc_number') AS noc_number,
       json_extract_scalar(labelled_json, '$.payload.data.noc_br_brandname') AS brand_name,
       json_extract_scalar(labelled_json, '$.payload.data.noc_br_din') AS din,
       raw_completeness_status
FROM optima_metadata_engine.source_observations
WHERE source_key = 'canada_noc'
  AND source_record_id LIKE 'product:%'
ORDER BY rand()
LIMIT 20;
```

## Scope and owner actions

**No new key, account or access task is needed for these public APIs.** Optional owner task: run the SQL above and inspect representative payloads.

This review covers all notices and returned product records in the NOC APIs, not every marketed Canadian medicine, linked monographs/review dossiers, or reconstructed historical database vintages. Health Canada describes NOC history beginning January 1994 for human drugs and September 2000 for veterinary drugs, with earlier veterinary population incomplete. Its separate Drug Product Database is the broader product-register route. [Official NOC API guide](https://health-products.canada.ca/api/documentation/noc-documentation-en.html), [DPD API guide](https://health-products.canada.ca/api/documentation/dpd-documentation-en.html).

All 15 existing collection worker instances were active; the metadata worker's last run succeeded and its timer was active. The controller timer was active and its last completed result was successful. Other sources' existing validation holds and the unrelated controller gap-audit/code-backup failures remain separate; this repair is not evidence that every source is healthy. Owner-requested source pauses remain intact. Runtime evidence: `worker-check-command-result.json`, `final-status.json`, `products-status-command-result.json` and `final-runtime-command-result.json`. After the successful replacement replay and full Athena verification, the superseded repair attempt’s failed flag was cleared; its journal/traceback evidence is retained in `product-error-command-result.json`. Final worker failed-unit check: `verified-cleanup-command-result.json`.
