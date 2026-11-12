# EPO OPS collection

Activated 2026-10-26 21:18 CET using the existing shared secret. Source: `epo_ops_patent_legal_events` (catalog 074).

Historical collection runs on **m7i.large**, within the existing 15-worker pool and aggregate **2-CPU / 6-GiB** limit. The t3 controller dispatches `constellation-specialist-epo_ops_patent_legal_events.service`; it does not execute historical payloads. Daily collection joins the existing `constellation-public-api-daily.timer` fairness schedule on t3, with its private source workspace/checkpoints.

The configured scope is **496 enabled company/alias query groups** from the pinned company universe. Canonical names and existing aliases are discovery candidates; they do not establish ownership, subsidiary equivalence or a verified entity match. Historical discovery covers publication years 2016 onward plus an earlier 1900–2015 bucket, which is split when OPS would truncate results. The legal lookup retains gazette-dated events since 2016, plus events whose date is unknown. Provider gazette, effective, created/exchanged dates and current observation times remain distinct. No historical availability timestamps are invented.

Daily discovery overlaps seven days. Known patents are registered in S3 and refreshed through 16 shards, with at most 50 references per shard/task. The cursor advances only after a native page commit; an interrupted request cannot silently skip a patent. This is a rotating refresh, not a promise that every known patent is rechecked every 24 hours. New unattempted jobs and retained partial jobs share the native scheduler. Aliases, quotas, provider coverage and lookup failures can leave incomplete scopes.

Both hosts share one request connection, a three-second pacing reservation, a 3,000-request daily cap and a conservative 512-MiB rolling seven-day response budget. Provider HTTP errors stop or defer the relevant source; no automatic purchase or quota upgrade is configured. Keys and OAuth tokens are neither stored in collection evidence nor logged.

## Verified startup

The historical validation committed **5 normalized event observations** with gazette dates **2017-02-15–2018-07-25**. Daily refresh committed **5 re-observations of the same events**. These are not ten distinct events. Both batches were independently read from S3 and SHA-256 checked. The historical task remains partial and has a resumable cursor. Regular historical queue state at this report: `[{"status": "pending", "jobs": 1}, {"status": "succeeded", "jobs": 2}]`. Daily timer: `active`.

[Activation and capture receipts](activation.json), [historical batch verification](historical-verification.json), [deployment](deployment.json). Native output uses `specialist_inputs`; the shared-table publication visibility check is shown below. Athena availability for these newly committed batches is not yet verified.

## Validation and limitations

**66 targeted tests passed**, including parser date semantics, unknown dates, amendments/deduplication, oversized search splitting, failed-lookup cursor preservation, no-results handling and credential redaction. EPO native records retain source XML and immutable raw-evidence references. `epo_ops.py` implements provider access; `additional_source_plan.py` defines scopes; the existing native collector supplies commits/checkpoints.

No complete 2016–present source coverage is claimed. Publication-window discovery and patent lookups do not measure day-by-day legal-event coverage, so failed lookups and quota deferrals remain operational receipts and are not converted into invented calendar gaps. The existing gap rule remains: verified dated gaps longer than five days are flagged in the 24-hour checkup; five days or less are recorded only. NICE remains paused.

Publication visibility query (not yet verified to return these records):

```sql
SELECT source, dataset, record_id, ingested_at, event_at_json, source_url
FROM optima_collected_data.observations
WHERE source = 'epo_ops_patent_legal_events'
LIMIT 25;
```

Official reference: [EPO OPS guide](https://link.epo.org/web/searching-for-patents/data/en-ops-v3.2-documentation-version-1.3.20.pdf).

Latest recurring-scheduler snapshot: **269 historical observations** across 13 attempted tasks; **5 daily observations** across 3 tasks. Neither scheduler reports a failed task in this snapshot; partial tasks retain `page_budget` cursors. These are observation counts, not unique events. [Current progress](current-progress.json).
