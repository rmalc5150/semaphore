# ClinicalTrials.gov repair — November 9, 2026

ClinicalTrials.gov is reviewed after raw-response validation, production metadata replay and actual Athena queries. This is a verified pipeline sample, not completion of source history.

## Root cause and repair

The old 2.0.2 generic metadata contract had an empty host allowlist and could not validate ClinicalTrials.gov study responses. Four separate failed batches stopped this source; raw capture continued. New immutable contract 2.0.3 and `metadata_engine/clinicaltrials.py` validate the official HTTPS API route, reject projected requests, match a unique NCT identity and require the complete collected study to equal its original API response, including substantive protocol/status sections. Request receipts and mismatched studies cannot pass.

All four failed batch slices passed (128 records). Superseded/requeued 33 old-version jobs, preserved failure evidence and reset the source to enabled. Four distinct jobs were accepted and published; the replay's five requested IDs included one duplicate. Reviewed-source date-queue handling is installed in local config, installation defaults and the worker runtime. Individual failures remain recorded without re-stopping this reviewed source. No captured data was deleted.

**41 focused tests passed**, plus installation-script compilation.

## Athena verification

- Original aggregate query: `f5e0d698-fd4f-4d40-8aeb-4eca0a700370` — **128 observations, four distinct raw batch URIs, all 128 raw complete**, latest ingestion November 9 at 10:25:28 UTC.
- Full metadata payload: `43701c23-9bf7-40ca-8ee3-5cde6669244a` — `NCT05651932`, complete original study, raw URI, validation labels and provider evidence.
- Curated payload query: `22cad31b-c02c-4474-b7b9-0b9ec10b5e93` — NCT IDs, titles, recruiting statuses and 13,290–15,255-character study JSON.

Run the existing aggregate query again. To inspect the actual fields of newly published study records:

```sql
SELECT source_record_id, ingested_at, raw_s3_uri,
       json_extract(labelled_json, '$.payload.data') AS full_study_json
FROM optima_metadata_engine.source_observations
WHERE source_key = 'clinicaltrials_gov'
ORDER BY ingested_at DESC
LIMIT 20;
```

`labelled_json` retains the full provider study under `payload.data`. Company links are candidates, not confirmed legal identities. Optional results sections depend on provider availability. Last-update-date historical queries return current study versions, not historical snapshots.

The curated regulatory window table's latest checked observation is **October 15**. The newest captured calendar window (October 22–23) has a partial 300-record manifest. Do not confuse the repaired and fresh metadata table with completion of curated-window catch-up. Remaining capture and publication can continue from retained checkpoints; no owner credential action is needed for ClinicalTrials.gov.

## Runtime health and repaired controller

Daily and historical collection controls both permit work. The controller's metadata timer is enabled; worker metadata timer and independent disclosure/RSS repair timers are active. Fresh accepted jobs were observed across ClinicalTrials.gov, CAISO, SAM.gov, HKEX, personnel, FRED and other sources. Worker health details are saved in `worker-health.json`; collection controls in `collection-controls.json`.

The metadata controller had twice timed out while memory reclaim from a large EDINET process saturated the shared data slice. Created a sibling `optima-metadata.slice` with 192 MiB MemoryHigh, 256 MiB MemoryMax and zero swap; moved only the controller into it, retaining its existing bounded memory/CPU. Successful later cycles completed discovery and five-batch publication. Persisted the unit, drop-in and installer changes. EDINET's heavy collection workload remains separate and does not establish full source health.

The worker has no failed systemd units. The controller's separate `ec2-code-backup.service` remains failed; it is not a capture/metadata failure. Final source-state snapshot: 77 enabled, 74 raw-stopped, five owner-paused, four access-layer. Other raw-validation holds and queued publication remain visible; no claim that every source is ready. Preserved owner pauses.

## Evidence

`failed-batch-validation.json`, `migration.json`, `metadata-deployment-result.json`, `replay-result.json`, `publication.json`, `athena-verification.json`, `metadata_sample.json`, `curated_payload.json`, `final-status.json`, `review-policy-result.json`, `worker-health.json`, `controller-health.txt` and `tests.log`.
