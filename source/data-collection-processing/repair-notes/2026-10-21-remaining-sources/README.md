# Remaining-source repairs — 21 October 2026

## Result

Individual repair steps and fresh Athena checks completed. Five of the six sources have no failed scopes in the checked specialist daily/historical scheduler state. SAM.gov remains blocked by provider HTTP 429. These checks do not certify complete source archives or specialist-ready entity mappings.

| Source | Work and verified result | Outstanding limitation |
|---|---|---|
| CAISO | No remaining failed specialist scopes to replay. Fresh queries verified the repaired 120-record scope. Shared publication also verified 1,456 ancillary-price records, 11 archive-inventory records, 1,020 price-interval records and 10 storage-indicator records captured before this maintenance. | Scope completion is not full market/history coverage. |
| Europe PMC full text | Replayed both remaining failed articles, PMC8098748 and PMC8740779. Both captured, published, checkpointed and queried successfully; two new records verified in shared Athena publication. | Rights and company/product links remain separate from content availability. |
| EIA generator files | Rechecked and republished eligible completed scopes as needed; fresh Athena queries verified 1,826 records from the August 2026 workbook. There are 54 complete historical scheduler scopes and 12 complete daily scopes. | 22 daily scheduler entries are deferred as `eia_report_not_published`; these are not 22 distinct missing monthly reports. Do not manufacture data for unpublished periods. |
| USPTO assignments | Replayed all four remaining disk-space failures. They returned 6, 3, 1 and 3 events: 13 total. Every scope was published and independently queried; shared publication also verified the 13 records. | Coverage is limited to the reviewed application set. Assignment events do not certify current ownership or chain completeness. |
| MLPerf | No remaining failed scopes to replay. Fresh queries verified the repaired repository index and an actual performance-log artifact, including its content, pinned commit and path. | Raw benchmark logs are available; comparable metrics and company mapping require downstream interpretation. |
| SAM.gov | Replayed a previously disk-blocked historical scope; the live request returned HTTP 429. Stopped further manual retries. Fresh queries verified an earlier successful 143-record historical scope. | 11 historical failures remain (7 now recorded as HTTP 429 and 4 not retried after the throttle); 2 daily scopes remain partial. Do not label these complete. |

## Engineering repair

Targeted publication previously loaded every historical publication-queue entry before filtering to one requested window. `window_publication.py` now directly loads requested canonical windows. Explicit repair-alias requests still use full duplicate-manifest checks; ordinary full-queue publication retains those checks too. This avoids unrelated queue discovery during individual repairs without deleting queued metadata or data files.

Ten focused publication, repair-report and runner tests passed. Individual executions use durable logs, explicit exit codes and S3 checkpoint evidence. Both detached repair supervisors exited successfully; the separate failed SAM attempt remains visibly failed in its own result.

## Athena evidence

- [Fresh checks of all six sources](fresh-athena-checks.json): actual count/sample query IDs and receipt-hash validation.
- [New repair receipts and payload samples](athena-receipts.json): all four assignment scopes and both PMC scopes verified; SAM failure explicitly unverified.
- [MLPerf performance artifact](mlperf-artifact-athena-sample.json): query `c1e63046-d2a9-4b46-bc79-a7ba70e1bb43` returned original benchmark log content.
- [Shared publication log](athena-publication.log): six new batch groups verified, totaling 2,512 observations, including the 15 new repair records and previously captured CAISO batches.
- [Final scheduler state](final-scheduler-audit.json).
- [SQL checks](SQL-checks.md).

An initial exploratory MLPerf query used the wrong payload-kind literal and was cancelled; the corrected query above succeeded. It was an audit-query correction, not a source failure.

## What you need to do

1. No new credentials, storage purchase or instance upgrade is currently indicated for these repairs. All 66 previously active timers were restored and checked; Reddit, Bluesky and GitHub remain paused.
2. Run the SQL checks below to review the payloads and judge whether their fields meet your specialist-layer requirements.
3. SAM.gov: wait for the provider's throttle to clear. The actual reset time was not supplied by this check; the configured shared local limits remain 40 requests/day and 10/hour. The normal authenticated collection schedules are restored, with their existing retry/budget controls.
4. If SAM.gov continues returning 429 on later scheduled attempts, check the account's API quota or contact SAM.gov support to confirm the allowance for this key. Request allowance information, not a replacement key by default. Do not send the key in support messages. Earlier successful results demonstrate that this is not established as an authentication failure.
5. EIA: no manual action for reports the publisher has not released. Collection continues to check availability through its normal schedule.

No claim is made that historical backfill is finished. Remaining SAM requests and daily partial scopes will need successful capture plus Athena verification before being considered repaired.
