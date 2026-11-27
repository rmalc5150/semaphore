# November 27 alert review

This was a read-only investigation of live services and S3 monitoring history. No schedules, limits, alert rules or collector configuration were changed.

| Digest item | Verified evidence | What the digest missed |
| --- | --- | --- |
| OpenAlex | The public snapshot checkpoint reached part 1,302 of 1,898. An earlier January 2016 API capture query, `1a4da6bf-2e17-4316-bd94-f94c5063dd3d`, succeeded in Athena. | The monitor still reads catalog/access entries that say the key is pending and the collector is unimplemented. The snapshot uses public S3 access. |
| KAKEN | S3 shows 31,059 unique projects and 16 published batches for FY2016. FY2025 is complete with 29,126 records and the cursor points to FY2026. Prior historical Athena query `0780fe8f-a5e2-46b1-9ffa-5591706271ec` succeeded. | The monitor reads old access and implementation flags. The separate controller daily service's journal reports `LoginRefreshRequired`, an AWS session error rather than rejection of the KAKEN application ID. |
| Google Patents BigQuery | Working controller catch-up route. Collection and Athena publication both reached April 2018 exclusive, with 27 verified months and 1,334,227 records. | The monitor checks the staged C7 migration route rather than the controller backfill that is already collecting and publishing. |
| Finlight | January 1, 2016 provider sample. A separate January 4 sample returned five articles in successful Athena query `ead369b5-074f-44c5-b999-76017d3d8040`. The separate earlier archive cursor reached April 14, 2016 exclusive. | The monitor checks the primary archive's 2021 start and ignores the configured earlier range. Collection cursor is not a publication receipt for the entire range. |
| SAM.gov | The collector enforces its configured 10-request daily cap locally. The code schedules a budget-limited retry after 00:05 UTC. The assessment at 10:05 UTC had no active SAM incident, and authenticated capture had verified progress at 09:17:35 UTC. | A local admission cap was presented as a generic repair. The actual provider allowance remains unconfirmed. |

## High SMS

S3 recorded the high SMS at 06:05:38 UTC. The daily audit had finished at 06:04:55 UTC with no query, receipt or sampled S3 failures. Its follow-up health exporter ran inside the daily audit's read-only sandbox, where it could not write the optional batch-verification cache at `state/collection-health/`. The standalone health service has permission to write there, which explains why the 06:30 health run and 06:35 watchdog check cleared the high incident. This can recur on the next daily audit until its follow-up uses a writable cache location or skips caching.

Exact alert payload is in `inspection-history.json`. Watchdog checks at 06:05, 06:35 and 10:05 UTC are saved alongside it. The latest inspected state had only the two previously known market coverage alerts.

No new key, federation change, purchase or manual restart is needed from the owner for these items. Engineering changes would reconcile the digest with the actual historical routes, classify the SAM cap as a scheduled wait, and give the daily audit follow-up a writable cache location.

## Follow-up repair at 10:39 UTC

The live historical blocker check now reads the OpenAlex snapshot checkpoint and KAKEN fiscal-year checkpoint under the active research-feed control, the controller patent catch-up timer and its pinned S3 stream, and the configured earlier Finlight range and its provider probe. It no longer uses the obsolete catalog flags or the staged C7 migration to decide whether those routes are blocked.

The normal systemd exporter completed successfully. S3 `health/latest.json` at **10:39:03 UTC** has no inspection errors and zero historical capture blockers. The digest renderer also omitted the blocker section and retained the separate historical and other data gaps. See `health-after-route-fix.json` and `overview-preview-after-route-fix.txt`. All 24 targeted tests passed, including checks that missing evidence or a stopped unfinished patent route is still surfaced.

This follow-up changed only historical blocker detection. No collector, checkpoint, email schedule, SAM cap handling or daily-audit cache behavior was changed.
