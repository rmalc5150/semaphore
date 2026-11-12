# EMA CTIS — reviewed and resumed, November 10, 2026

Owner raw-data review is recorded in entry 16 of `RAW_DATA_VERIFICATION_SCHEDULE.md`. Technical replay, original-provider validation and Athena readback passed. No CTIS credential action is needed.

## Cause and repair

Valid CTIS API records already existed, but a separate public route supplied discovery-page receipts. Four failures from that route tripped the source-wide metadata circuit breaker. The source was stopped despite usable saved API details.

Added `metadata_engine/ctis.py` and immutable contract 2.0.3. Validation requires the official HTTPS detail endpoint and matching CT number; a trial's complete detail must exactly equal the saved original response. Derived submission/decision records must match the original application or decision object and composite identity. Search summaries, discovery pages, mismatched trials and request-only evidence cannot pass.

Deployed the validator and contract to the worker, persisted reviewed-source date-queue handling in runtime/local configuration and installation defaults, superseded/requeued 65 unfinished old-contract jobs, and resumed the source. Raw objects and failed-attempt reports are retained. Individual invalid discovery pages remain gaps and no longer stop this reviewed source or other pipelines.

Production replay checked 17 selected jobs: **two API batches accepted (35 records)** and **15 discovery receipts correctly rejected**. The generic replay helper returned exit 2 because it expected every input to be accepted. A separate explicit verification asserted these two expected outcomes (`replay-verified.json`); the diagnostic unit's failed flag was reset only after that verification. Its journal is retained. This is not a claim that discovery receipts are fixed or complete data.

**34 focused tests passed**, plus Python compilation checks.

## Athena readback

- Metadata aggregate `b56daedd-f9be-4b08-92b8-c8f377c1c516`: **1,996 observations, 84 distinct raw batches, all 1,996 raw-complete**. Latest ingestion November 9 at 17:36:56 UTC.
- New contract payload checks: `1b80b1fb-6080-43b1-89b9-336c34e5dbeb` (subsequent equivalent readback saved in `metadata_sample.json`). Trial and regulatory-event rows are contract 2.0.3 with complete labels and original API evidence.
- Published two complete/exhausted curated windows for **November 6 and November 8**: **14 trial records and 21 regulatory events**, total 35. Canonical staging checks and publication receipts passed.
- Post-publication curated payload query **`0a54994b-74dd-4eb4-9a76-117d5262269a`** returned fresh rows with November 9 observation time, trial identities `2026-527193-36-00` / `2026-526189-25-00` and **74,047 / 94,524-character** trial detail payloads, plus a matched decision event.

The query in the verification schedule can be rerun unchanged. To inspect provider fields:

```sql
SELECT source_record_id, ingested_at, contract_version,
       json_extract(labelled_json, '$.payload.data') AS provider_data
FROM optima_metadata_engine.source_observations
WHERE source_key = 'ema_ctis'
ORDER BY labelled_at DESC
LIMIT 20;
```

For curated trial details and events:

```sql
SELECT *
FROM optima_regulatory_pilot.research_records_windows
WHERE source = 'ema_ctis'
  AND window_id IN (
    '62d74473c70fca21b31089e069aa00f4cf6817491dbc8f35729a3a6292b58388',
    '65a2c458f121c8da552eb3e855d9193c1bcf57b85989782c7bab099599c4f57e'
  )
LIMIT 20;
```

This reviews **current public structured trial records and matched events**. It does not certify download of every linked document, confidential/pending trials, point-in-time historical versions, or complete history beyond CTIS search/disclosure limits. The collector retains its 10,000-result cap and marks incomplete scopes accordingly. Company matches remain candidates.

## Capture and engine health

- Daily and historical collection controls both allow work.
- All **15 worker services** are active: five native, six legacy, four public.
- Metadata worker timer restored after deployment; successful eight-job cycle observed. Metadata controller timer enabled and latest result success in `optima-metadata.slice`.
- Daily collection and research-publication timers enabled; services were running/waiting under their normal shared workload lock. Historical dispatch timer active. Existing CTIS API capture produced the verified November 9 batch; existing schedules continue from checkpoints.
- Owner pauses are preserved. No mass restart or raw-data deletion was used.
- Worker final failed-unit list is empty. Controller has two separate failed units: `optima-product-search-daily.service` (`Unknown database 'tracking'` during product-directory lookup) and `ec2-code-backup.service`. Product-search retry timer is enabled, but that source needs directory/schema reconciliation before a meaningful replay. These failures do not stop CTIS.
- Final source-state snapshot is in `final-status.json`; other raw-validation holds remain. Engine availability is not an assertion that all source contracts or histories are complete.

## Saved evidence

`before.json`, `sample-record.json`, `failed-batch-validation.json`, `migration.json`, `metadata-deployment-result.json`, `replay-result.json`, `replay-verified.json`, `publication.json`, `athena-verification.json`, `metadata_sample.json`, `fresh-publication.json`, `curated_payload.json`, `collection-controls.json`, `worker-health.json`, `worker-final-result.json`, `controller-timers.txt`, `controller-failed-units.txt`, `final-status.json`, `tests.log`.
