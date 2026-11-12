# openFDA repeat query check — November 10, 2026

The owner reports an empty Athena result. A fresh execution of the aggregate query, explicitly qualified with `AwsDataCatalog` and with cached-result reuse disabled, returned **75 observations / five linked raw batches / 75 complete raw observations**. Query **`33f10377-35d6-43af-bfff-66d1318d843a`**, 5,960 bytes scanned. The earlier repair remains in place; a new backend disappearance was not reproduced.

Use these same settings in the Athena console:

1. AWS account **059416028963**.
2. Region **US East (N. Virginia), us-east-1**.
3. Data source **AwsDataCatalog**, workgroup **optima-collected-data**.
4. Disable **Reuse query results** and run the updated query from verification-schedule entry 17.

```sql
SELECT source_key,
       count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations"
WHERE source_key = 'fda_openfda'
GROUP BY source_key;
```

If this still returns no rows, the failing execution ID is required to establish whether its query, catalog, region, account or access context differs. Cache/context differences are possibilities, not established causes of the owner's result. Do not change SQL to `drugsfda_applications`: that is a distinct source and separate review entry.

After the initial check, published **two newly accepted batches**. Final aggregate query **`214f3440-5582-4180-9ef6-660f1bc741f1`** returned **108 observations / seven linked raw batches / 108 complete observations**. This confirms ongoing metadata-to-Athena progress.

## Current pipeline checks

- `fda_openfda` remains **enabled**, immutable contract 2.0.3, zero consecutive raw failures and no last error. Further jobs are queued; additional jobs have been accepted since the earlier verification.
- Daily and historical collection controls both permit work.
- All **15 worker services** are running. Metadata worker timer is active; its last observed cycle processed eight jobs successfully.
- Metadata controller's last result is success; its timer, daily collection, research publication and historical dispatch timers are enabled/active. Shared collection/publication services were running or waiting for their serialization locks.
- Metadata payload query `3c0d45f8-2ffa-4ec2-8783-eb6c191a849c` and curated payload query `367283fb-e28e-4a69-a911-4b968c303485` both returned application IDs, `AP` submission status and nonempty provider JSON.
- Checked source-specific pending publication separately; see `publication.json` and `athena-verification.json` for its final aggregate.
- Five owner-paused sources remain paused. Other sources have **83 raw-validation holds** at this check; these are not made healthy by a running engine. The separate code-backup service remains failed. Product search now reports its known missing-product-entity dependency rather than a database exception.

No all-source restart or new raw-data exclusion was performed. openFDA remains marked reviewed. The latest checked nonempty ingestion remains **October 31**; working queries do not establish current-day freshness or finished catch-up.

## Evidence

`exact-athena-query.json`, `final-status.json`, `metadata_sample.json`, `curated_payload.json`, `worker-health.json`, `collection-controls.json`, `publication.json`, `athena-verification.json`.
