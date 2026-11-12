# EMA medicines — repaired and reviewed, November 10, 2026

Entry 19 (`ema_medicines`) is reviewed. The selected MHRA query is a different source; use the EMA query below. No new API key or owner access step is required.

## What failed and changed

The original full EMA report JSON was saved, but generic substantive-content checks did not recognize its medicine fields. Four failed batches tripped the metadata circuit breaker. The allowed host was already correct; this was not an empty-host/key problem.

Added `metadata_engine/ema_medicines.py` and immutable source contract 2.0.3. Validation checks the exact official report URL, SHA-256, unique EMA product identity, complete equality with its original provider row, medicine name and official record link. Projected/index/request-only data cannot pass. Validated all four failed batch slices (128 records), requeued 40 unfinished old-version jobs, resumed the source and installed reviewed-source date queues locally, remotely and in installation defaults. Original failure evidence is retained. Both earlier-batch and fresh-batch production replays passed.

## All-provider capture verified

The daily adapter reads every medicine row without a company, category, status or first-publication-date filter. Historical mode retains its explicit first-publication-date grouping; it does not establish historical provider vintages.

Installed **`optima-ema-medicines-daily.timer`** on the collection worker: **07:35 Europe/Madrid**, persistent calendar schedule plus boot catch-up. One full report per capture day, 384 MiB memory limit, 20% CPU, five-minute timeout. Uses normal source raw commits, private worker publication queue and existing provider controls; no IAM expansion. Pinned universe context supplies envelope validation only and does not filter the medicine set. Daily source configuration routes this source to the dedicated lane, preserving historical routes and avoiding duplicate shared daily execution.

Fresh November 10 capture reconciled **all 2,757 provider rows to 2,757 saved unique EMA product IDs**:

| Category | Medicines |
| --- | ---: |
| Human | 2,357 |
| Veterinary | 400 |

All statuses are retained: authorised 1,871; withdrawn 434; application withdrawn 286; refused 69; opinion 33; lapsed 29; expired 19; revoked 10; suspended 2; opinion under re-examination 2; withdrawn from rolling review 2. No missing/unknown date is replaced by an invented historical date.

“All” means the complete published EMA report. It does not establish coverage of every nationally authorised medicine, every investigational drug, linked EPAR documents or historical versions.

## Athena evidence

The entire fresh report is already published in `optima_specialist_inputs.source_observations_windows`:

- Count/distinct-ID query **`6532bb35-9a44-497d-9f62-9ef42385f6bf`** returned **2,757 rows / 2,757 unique medicines**.
- Category query **`9aeddc8a-7839-46ec-b19a-63bc55530a30`** exactly matched 2,357 human / 400 veterinary rows.
- The source manifest and canonical publication receipt are complete/exhausted and verified. See `fresh-capture.json`, `fresh-publication.json`, `snapshot-athena-verification.json`.

Inspect all columns and medicine JSON in this exact snapshot:

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE source = 'ema_medicines'
  AND window_id = 'a22b2edb0bad938ca84cce66d2cdf5f3e192090217285647d7e6308f1407759e'
ORDER BY rand()
LIMIT 20;
```

The metadata aggregate query now returns **160 raw-complete observations / five raw batches**, including November 10 capture. Query **`c16271e6-6138-43eb-8260-7ee1c5d2360d`**. Remaining metadata labels continue separately; 160 is a processed-observation count, not a count of the medicines saved in the complete curated snapshot.

```sql
SELECT source_key, count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations"
WHERE source_key = 'ema_medicines'
GROUP BY source_key;
```

Use **us-east-1 / AwsDataCatalog / optima-collected-data**, with query result reuse disabled. Original report fields remain under `payload_json.data` in curated rows and `labelled_json.payload.data` in metadata rows. Entity links remain candidates.

## Checks

**43 focused tests passed**, including original-row equality, projection/identity/duplicate/origin rejection, daily retention of veterinary/refused/undated rows, queue-bridge regression checks and existing metadata runtime tests. Edited modules compile.

All 15 standard collection workers are active. Metadata worker/controller and historical/daily/publication schedules were checked online; new EMA service completed successfully and its next calendar trigger is set. Daily and historical collection controls permit work. Other raw-validation holds and owner pauses remain separate. The unrelated controller code-backup service remains failed.

See `worker-check-command-result.json`, `collection-controls.json`, `final-status.json`, `metadata_sample.json`, `curated_payload.json`, deployment/replay receipts and `tests.log` for bounded verification evidence. Systemd units are also saved under the repository's `systemd/` directory.
