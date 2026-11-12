# Reviewed SEC company facts and runtime check — November 9, 2026

## Review recorded

SEC company financial facts (`sec_companyfacts`) was already checked in RAW_DATA_VERIFICATION_SCHEDULE.md. Added explicit owner review date, November 9. Applied the same nonblocking source/date failure mode used for the five other reviewed sources, on controller and worker and in the installer. Raw validation still applies; input failures remain recorded. No unrelated raw-stopped source was resumed.

Live source state: enabled, zero consecutive raw failures, no last error. Source jobs at the sampled check: 464 accepted / 14,704 output rows, 191 queued. Athena readback returned 8,439 observations, all raw-complete, referencing 198 raw objects. Query: 8806149a-dbc8-4c42-b802-43822f5f07b2; 365,422 bytes scanned. Latest ingested_at in that published sample: October 26, 2026. This verifies retained published data, not current-day SEC fact freshness or complete processing of the backlog.

## Runtime repairs

- S11 daily content service was failing on a missing symlinked universe configuration: it had not been routed through the shared S3 runtime. Installed a reversible 99-s3-runtime.conf override preserving its payload command, limits and accepted partial/timeout exits. It now queues through the global resource lock and hydrates/checkpoints state normally. Its first post-repair payload completion is not yet verified.
- Eight enabled daily services had stale failed maintenance conditions and elapsed timers. With the maintenance marker absent and owner source pauses preserved, explicitly started their existing units. Public archive and daily raw services subsequently completed and committed new source receipts. Other restored enrichment units are running/queued behind the shared resource lock. See overdue-daily-starts.json.
- Restored the existing disabled company-catalogue timer and queued its existing bounded command. No source-specific owner pause applied to it. Post-resume processing completion remains pending.
- The main daily runner uses exit 2 for bounded partial work and commits its progress before exiting. Added SuccessExitStatus=2 alongside existing 75; structured source errors and unmet dependencies remain in reports. Queued its normal continuation; no data scope was marked complete by this service change.
- Twenty metadata-runtime tests passed. An initial config-only worker deployment appended a literal newline escape; corrected it and added JSON validation before atomic replacement. Subsequent worker processing and the final configuration readback succeeded.

## What is running

Remote worker inspection found 5 raw historical workers, 6 legacy historical executors and 4 public artifact workers active. The minute-scheduled metadata worker processed 8 jobs in 19.53 seconds, including accepted market/NASA/Zenodo/USGS outputs, while recording per-source raw failures and retries. The metadata controller completed intake, discovery and publication stages; accepted jobs increased from 5,633 to 5,658 over the sampled interval. These counters are live, not fixed totals.

The committed-data Athena publisher last verified 101 partitions / 44,962,296 records at 14:15 UTC (15:15 CET). Current invocations are queued through existing resource locks. This count is publisher-level and does not establish every source's raw-content completeness.

## Remaining limitations

Infrastructure is running/scheduled; the source corpus is not uniformly healthy or complete. Metadata state includes 79 raw-stopped sources, 5 owner-paused sources and 4 access-layer entries. Raw failures and missing-artifact repairs remain explicit. Shared-lock waits, older incomplete scopes and publication catch-up remain. No blind resume of those source holds was performed.

After the repairs, systemd listed no failed collection/metadata services; the separate ec2-code-backup.service retained an older failure. That backup is outside this data-pipeline check.

No new owner credential, purchase or approval task is required by this check. Continue the raw-data reviews in the schedule.
