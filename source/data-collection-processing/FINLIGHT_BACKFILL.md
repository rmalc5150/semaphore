# Finlight temporary upgrade and downgrade notice

Updated 2026-10-11. The user upgraded to **Pro** and requested notification as soon as historical collection is finished so they can return to **Pro Light**.

## Verified access

The existing `newKeys` / `finlight-api-key` credential returned dated articles for January 2021, January 2024, and October 9, 2026. [Probe evidence](reports/finlight-upgrade-probe-2026-10-11.json) includes immutable S3 evidence references. Three successful requests were made; no replacement credential is needed. This verifies sample archive access, not full archive completeness.

## Collection scope and scheduling

- Fixed backfill interval: **2021-01-01 through 2026-10-10 inclusive**.
- Four existing sector-term queries, each in English and Chinese; eight searches per day. This is the existing news collection scope, not every article or every company mention.
- Existing hourly `optima-news-collection.timer` runs the separate Finlight archive after daily/reconciliation work. Both news collection and publication timers were confirmed enabled; their services were queued at setup time. A first historical commit is not yet verified.
- Existing `optima-news-publication.timer` publishes queued news windows and checks completion receipts. No separate timer or subscription purchase was added.
- `config/finlight-backfill.json` controls the finite backfill; `config/news-history-finlight.json` pins its queries and observed archive access.
- Existing daily configurations and stream identities remain unchanged, preserving checkpoints. During this upgrade the worker overrides Finlight's old 40-request daily limit using the separate backfill control. The old daily configuration's plan label is retained for checkpoint compatibility; it is not a statement of current account entitlement.
- Separate S3 collection/publication cursors live under `operations/news/finlight-backfill/<scope-hash>/`. The hash includes configuration, interval, universe and taxonomy. Partial tasks retain their exact page checkpoints.

## Budget

Finlight daily, reconciliation, probes and archive requests share one durable daily counter. The active ceiling is **1,000 requests/day**, with at most **100 archive requests and four completed dates per invocation**. Retries count. Rate/quota errors stop progress rather than declaring empty history complete.

The user specified “Pro,” without an exact tier or monthly allowance. Published [pricing](https://finlight.me/pricing) lists Pro Standard at 50,000 requests/month and Pro Scale at 150,000; 1,000/day uses at most 31,000 in a 31-day interval from these jobs, excluding other applications. Confirm the actual dashboard allowance and billing-period usage before accelerating. No unlimited entitlement is assumed. [Provider quota documentation](https://docs.finlight.me/en/v2/rate-limits/) describes monthly and burst limits.

No completion date is promised: actual article volumes, pagination, the shared job lock and Athena publication throughput determine duration.

## Completion email

`finlight_backfill.check_completion` runs under the existing news publication lock. It advances through each historical date only when:

1. Collection advanced beyond the date without skipping partial tasks.
2. All eight query/language combinations have complete, exhausted manifests for this archive configuration and exact date.
3. The publication receipt matches the current queued manifests and publication configuration.
4. The immutable Athena verification object passes SHA-256 verification and matches the window and release.

Only after the full interval is verified and the Finlight daily cursor has caught up through yesterday does it send **“Finlight backfill verified — ready for Light”** to the existing collection-alert email topic. This is the user's requested completion notification; no test notification was sent.

The accepted SNS message ID is recorded to suppress later sends. Failed sends retry on subsequent publication runs; an ambiguous SNS success followed by a failed receipt write can result in a duplicate. Email acceptance by SNS is not a delivery guarantee.

After a recorded notification, the daily client returns to its existing 40-request cap. The completed archive makes no further collection requests. **The subscription is never downgraded automatically.** The user can then downgrade, recognizing that Pro Light limits historical re-queries and does not include sentiment analysis. Extending or changing the historical scope later may require upgrading again.

## Validation

39 focused tests passed before deployment checks, including partial resume, missing language coverage, stale publication receipts, corrupted verification evidence, daily lag, notification retry and duplicate suppression. Live archive access was verified separately; full backfill and publication completion remain pending.
