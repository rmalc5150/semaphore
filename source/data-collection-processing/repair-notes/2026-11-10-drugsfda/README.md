# Drugs@FDA applications — November 10, 2026

`drugsfda_applications` is now reviewed and enabled. It is distinct from `fda_openfda` (approval/CRL events) and `ema_medicines`. The IDE-selected EMA query does not query this source; use entry 18.

## Metadata repair and Athena proof

The generic metadata validator rejected original full application JSON as insufficient substantive content. Its API host was already allowed; this differs from the earlier openFDA empty-host failure. Added immutable contract 2.0.3 and exact provider-result validation in `metadata_engine/openfda.py`: application identity and entire saved response row must match, with original products retained. Aggregates, field projections and request-only evidence cannot pass. SHA-256 raw checks remain.

Validated four failed batch slices (128 records), superseded/requeued 20 unfinished jobs without deleting raw data, reset the source and installed reviewed-source date queues locally, remotely and in installation defaults. All four bounded production replays passed. A fresh inventory batch was also replayed with normal source locking and lease fencing.

- Metadata aggregate query **`0cdbc852-4f68-4c51-a761-1907da862c6e`**: **192 raw-complete observations / five linked raw batches**, latest ingestion November 10, 11:16:29 UTC.
- Fresh metadata payload query **`0456ddc9-397d-4d41-93ff-965ee551fff4`**: `ANDA060291`, `ANDA060290`, `ANDA060286`, one/two-product arrays, full JSON and contract 2.0.3.
- Curated specialist payload query **`6b581467-5ad3-48c0-943d-b67de608da58`**: full applications and product arrays in `optima_specialist_inputs.source_observations_windows`. Newly captured inventory partitions are partial and are not falsely published as complete curated windows. Their validated raw batches are already accessible through metadata Athena; complete partitions enter the curated publication queue.

Use AWS us-east-1, AwsDataCatalog, workgroup optima-collected-data, result reuse disabled:

```sql
SELECT source_key, count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations"
WHERE source_key = 'drugsfda_applications'
GROUP BY source_key;
```

Full application/product inspection:

```sql
SELECT source_record_id, ingested_at,
       json_extract(labelled_json, '$.payload.data') AS full_application
FROM optima_metadata_engine.source_observations
WHERE source_key = 'drugsfda_applications'
ORDER BY ingested_at DESC
LIMIT 20;
```

## All applications/products, not a company sample

Existing collection retains full applications matched by submission dates and has no company/sector/marketing-status filter. Those date queries alone omit applications without activity in the covered dates. Added a dedicated current-inventory route:

- All ANDA, NDA and BLA six-digit application-number ranges, split by first numeric digit (30 nonoverlapping ranges).
- A complementary query covers every identifier outside those ranges. Its live probe passed and currently returned zero; unexpected identifiers are not silently excluded.
- No submission-date or product/company filter. Each complete application retains every returned product, including discontinued products and supplied submissions.
- Live unfiltered API total **29,447 applications**. Applications can contain multiple products. This is not the number of drugs already captured, a global medicine inventory or a claim that every FDA-regulated drug is in this dataset.
- Weekly scopes remain stable across resumptions. Per-partition total/revision pins reject mixed pagination vintages; changed scopes refresh instead of repeatedly using an invalid cursor. Current inventories are not historical snapshots.

`optima-drugsfda-inventory.timer` runs on the worker every two minutes after completion, up to two scopes/four pages per scope, 384 MiB RAM and 20% CPU, with existing provider HTTP controls. It is independent of the historical date queue and preserves daily/historical capture. The saved checkpoint verified **800 applications**, one partial partition and one completed empty partition; further pages/partitions remain. Source config records this as a dedicated inventory executor, avoiding duplicate inventory execution by the shared daily planner.

Raw inputs/manifests use the normal specialist contract. Worker-owned operational state:

`research-data/constellation-backfill/specialist-schedulers/drugsfda-inventory/state.json`

Completed partition receipts use the existing worker-authorized private specialist-publication prefix. `specialist_publication.py` bridges only the DrugsFDA inventory subfolder into canonical publication, idempotently; a bad bridge entry is separately recorded and does not stop other windows. No IAM expansion was required.

Initial deployment exposed two permission assumptions: direct access to the controller runtime index, then writes to the controller's publication queue. Fixed by deploying a checksum-verified universe context through the allowed deployment route and using worker-owned state/private queue prefixes. The pinned universe supplies the envelope context only; it does not filter application selection. Subsequent production inventory runs succeeded.

## Runtime and tests

All 15 standard collection workers are active. Metadata worker/controller and daily collection/specialist publication/historical dispatch schedules were checked online. Source metadata state is enabled, zero consecutive failures; other source holds and owner pauses remain separate.

**34 focused tests passed**, covering full application equality, all-provider planning, stable weekly scopes, pagination revision refusal, queue-bridge idempotence/failure isolation and existing metadata regression checks. Edited Python modules compile. A broader source-schedule suite encountered five unrelated failures: missing S3-hydrated schedule/universe fixture files and existing PubMed fixture/validator mismatches (`broader-tests.log`); these were not hidden or counted as passed.

No new API key or owner access action is needed. Inventory/history, linked application PDFs, historical vintages, company identity resolution and Constellation product-entity registration are not certified by this review.
