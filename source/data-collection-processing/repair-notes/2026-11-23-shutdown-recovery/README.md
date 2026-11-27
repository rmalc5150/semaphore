# Shutdown recovery and pipeline repairs — November 23, 2026

Times in this update are **UTC**. This is verification of running processes and named scopes, not certification that every source's history or specialist fields are complete.

## Shutdown evidence and current operation

The controller booted at **16:18 UTC**, after a kernel out-of-memory event at **16:16:51 UTC**. The retained log ends during the OOM trace and does not identify the final victim or establish the complete reboot cause. Do not assume a particular collector caused it. The controller is currently a **t3.medium with about 3.7 GiB RAM**; the existing data slice remains capped at 2 GB. No resize was requested or applied. About 1.9 GiB was available during the recovery check. Bounded repair jobs used explicit memory/CPU/runtime limits.

The M7 worker remains a running **m6a.xlarge**; its latest boot was **10:31 UTC**, before the controller event. All **15 historical executor services** were running: five native, six legacy and four public-source executors. Controller metadata intake, health and shared lifecycle timers were active. The final systemd checks found no failed units on either host after the additional Health Canada replay.

Ordinary metadata workers have live job leases. Indexed database probes showed accepted outputs continuing at **16:31**, **16:38** and **16:41 UTC**, after the controller reboot. Fifteen registry entries outside the ordinary enabled state were observed and retained, including internal `access_layer` routes; these are not all failed or stopped sources. Intentional owner pauses remain in force.

## End-to-end metadata verification

A genuine publication receipt was confirmed for metadata job:

`2e59115a9b31a4117fd2f1ce03f579d8ca3e1acb70f1ff6366e0f14149d19769`

The publication was verified at **16:41:33 UTC**, after the reboot. A fresh Athena query of its exact `optima_metadata_engine.source_observations` partition returned **32 EODHD rows, all with populated raw-source links**, matching the receipt. It scanned **921 bytes**. Query ID:

`8752e599-2630-4664-a9a8-73bfe4bbfc38`

See `metadata-publication-receipt.json`, `metadata-athena-readback.json` and `metadata-athena-check.sql`. This establishes that acceptance, publication and Athena access are working for this tested post-reboot path. It does not declare all newly accepted jobs published. Targeted diagnostic publication attempts that waited on the shared lock were not counted as successful publication; the proof above came from the normal publisher.

## Reported services

### Assignment history

The historical assignment service's latest invocations succeeded. Its reviewed capture state already contains **88 completed year/application scopes**, covering **eight explicitly reviewed applications**, with the configured history ending **October 10, 2026**. This does not establish coverage of every USPTO assignment.

The runner previously emitted nothing when all its planned scopes were already complete, leaving monitoring without sufficient recovery evidence for an old signal failure. It now emits the exact completed manifest references only when **every currently planned scope matches its saved job and is complete**. Missing, partial, changed or manifest-less entries cannot claim success. The worker patch was deployed and the normal service rerun. See `assignment-proof-result.json` for the actual completion summary. This is a capture-scope proof, not a claim that all assignment publication is complete.

### SAM / authenticated daily

A recovery defect treated only failed terminal manifests as eligible for restarting a changed SAM source; partial terminal manifests could resume a known-invalid offset indefinitely. Restart recognition now accepts both failed and partial source-change outcomes, while retaining all ordinary page and quota checkpoints. The fix is installed on the controller and active worker runtime copies.

A bounded replay of the exact failed job recovered **4,000 records** in a fresh generation, then returned **HTTP 429**. The durable controller quota log contained **11 requests that day**. The account's actual role/allowance is unconfirmed, including after the owner's “not sure” reply. The cap is now conservatively **10/day** pending confirmation. The normal runner then deferred at `sam_daily_request_budget` and persisted its state; other providers continue. Four committed SAM batches were handed to its **enabled** metadata source. They are not asserted Athena-verified here.

SAM's [official Opportunities API documentation](https://open.gsa.gov/api/get-opportunities-public-api/) says request allowances depend on the account role. The observed 429 does not prove a bad key, nor confirm that the exact quota is ten. Do not rotate keys or increase the local allowance to work around throttling.

### Core daily / disclosure prerequisites

The upstream HKEX forward cursor is behind the document/candidate forward cursor. That creates genuine incomplete date windows and a catch-up dependency; it is not evidence that unrelated collectors stopped. No prerequisite check was removed.

The earliest tested ready dates were replayed. An additional performance defect wrote a full S3 checkpoint for every rejected parent filing. The collector now checkpoints rejected-parent cursor progress in bounded groups of 64, flushes it at a record budget, and still commits every actual output record immediately. Tests cover a partial resume and a later selected record; there is no change to selection or classification.

After deployment, **October 14** completed with **10 full-content document records**, plus **four M&A and four strategic-transaction candidates**. Press-release and licensing scopes completed with zero matches. These are unreviewed textual candidates, not confirmed events. All five scopes were queued for native publication. Their internal metadata registry entries are `access_layer`, so the ordinary metadata-worker handoff correctly skipped them; that policy was retained. They are **not yet asserted Athena-verified**. Other pending dates, including October 15, remain catch-up work; this is not a blanket resolution of the service's prerequisite alert.

### Market OHLC consistency

This is a verified provider data-quality issue, not a numeric parsing failure. Archived 2016 responses contain **408 inconsistent bars across five symbols**:

| Symbol | Inconsistent bars | Example date |
| --- | ---: | --- |
| 2311.TW | 142 | 2016-01-04 |
| 2325.TW | 3 | 2016-06-20 |
| 3559.TW | 19 | 2016-06-20 |
| ABB.MC | 8 | 2016-01-14 |
| DD.MX | 236 | 2016-01-04 |

Their reported close lies outside the reported daily low/high. Some examples also have close equal to adjusted close, but a mixed adjustment basis remains a hypothesis for the provider to investigate. The collector must not invent a close, expand the high/low, substitute adjusted prices, or classify these as impossible trading-period exclusions.

Diagnostics now retain the exact offending date, provider OHLC values and required ordering, in addition to the original raw evidence. The patch was installed on the controller and named worker market runtimes. Existing symbol isolation lets other symbols continue. These five source windows remain incomplete until corrected or separately resolved with evidence. `market-invalid-bars.json` contains all affected archived bars; `EODHD-support-message.txt` is ready to send without an API key.

## Additional daily failure recovered

The broad recovery audit found `optima-canada-noc-daily.service` in timeout state. A replay through its existing bounded runner succeeded and reconciled **38,393 unique notices** against the official full-report response. The counts include prescription/nonprescription medicines, biologics, radiopharmaceuticals and veterinary products; this is a current full-report snapshot, not a historical vintage archive. Its publication was queued. The worker had zero failed systemd units afterward. See `final-worker-result.json`.

## What the owner needs to do

1. **SAM account allowance:** sign into SAM.gov and check the account's API/role information. If the daily allowance is not shown, ask the Federal Service Desk to confirm it and the supported account route for the intended automated public-data use. Copy `SAM-support-message.txt`. Share the confirmed allowance; do not send the API key. Collection will wait and resume within the conservative budget meanwhile.
2. **EODHD data correction:** send `EODHD-support-message.txt` to EODHD support. It identifies all five symbols, the request period, counts and example bars. Ask for corrected consistent OHLC data or a documented alternate route/adjustment basis. No replacement prices are assumed and no new subscription is requested.
3. Continue ordinary Athena payload reviews where publication is already verified. The tested metadata query is in `metadata-athena-check.sql`. Do not mark the newly queued disclosure, SAM or Health Canada captures Athena-ready until their own receipts/readbacks exist.

No manual worker restart or new AWS permission is requested. The collector/metadata repairs and remaining catch-up/publication checks are engineering work.

## Retained limitations

The 61 reviewed market exclusions and unresolved market-coverage counts remain separate from the OHLC issue. Recently expanded historical scope has increased the number of unfinished symbols; that increase is not itself proof of lost data. Source-specific validation restrictions, EDINET 2016's exclusion, and pauses on Reddit, Bluesky, GitHub source capture and Marketaux remain. No raw or curated data was deleted and no broad source restriction was lifted.

**105 relevant regression tests passed.** Original health/alert/worker snapshots, raw market evidence, per-source replay outcomes, worker database evidence, deployment receipts and live Athena results are saved alongside this note. Diagnostic attempts with no publication result or a query/setup error are not counted as successful recovery.

## Final alert reconciliation

The actual health service and metadata controller both completed successfully after reboot. The final saved health report has no monitoring errors. Alert reconciliation retained **six active low-severity incidents**, removed the old assignment signal incident after the 88-scope completion proof, and found **no active high-severity alerts**. See `health-after.json`, `alerts-after.json` and `alert-reconciliation.json`. No manual email or SMS was sent. Source quality gaps and publication/catch-up work remain explicit.
