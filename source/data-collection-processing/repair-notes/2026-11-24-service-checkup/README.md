# November 24 service recovery

## Repaired and verified

The shared temporary directory `/dev/shm/optima-s3` was absent. Many units failed with **226/NAMESPACE before executing their commands**. The boot initializer remained active/exited, so requiring it did not recreate the missing directory. The reason the directory disappeared has not been established.

Restored the directory through the existing initializer. Installed `optima-s3-runtime-ensure.service` and dependency drop-ins for 66 affected units. This idempotent oneshot reruns before namespace setup, without RemainAfterExit. Disabled start-rate limiting for this mkdir-only helper after a restart burst exposed the default limit. Future installation in `install_s3_runtime.py` includes the helper.

Validation: two isolated real systemd tests recreated a deliberately absent **test-only** directory before strict namespace setup; all 12 `test_s3_runtime` tests passed. No production directory or captured data was deleted.

- Authenticated daily: a SAM page committed; the window now has 2,000 cumulative records and remains resumable at its page budget. Verified S3 checkpoint at 17:46:42 UTC.
- ChiCTR: three resumable page-limit manifests; verified checkpoint at 17:49:40 UTC. This is execution recovery, not complete historical coverage.
- News: one newly completed 61-record Finlight batch plus another resumable batch; verified checkpoint at 17:52:08 UTC.
- People: feed scopes reconciled and personnel archive committed one record; verified checkpoint at 17:50:41 UTC.
- Global patent monitor and market service invocations returned normally. Market validation and coverage remain unresolved below.
- Overdue Athena/prosecution/specialist dispatch requests succeeded. Actual worker services are active/queued; dispatch success does not mean publication is finished.
- Daily audit saved at **17:52:19 UTC**: **147 successful fresh Athena queries**, including 140 source/dataset readbacks; no query failures. Sampled S3 verification: four manifests/two objects, no failures. Also checked the status of 12,347 earlier query receipts; those are not 12,347 new queries. See `daily-audit-summary.json`. This verifies existing published data, not every newly queued batch.
- All 15 historical executors were running on the worker. Reviewed metadata publication was actively preparing 12 sources in its fresh worker snapshot.
- Corrected unattended AWS credentials for patent gap catchup and code backup to use the instance role instead of expired interactive login. Patent gap catchup resumed committing pages. Backup encountered a separate oversized model asset afterward; see remaining work.

## Remaining work and ownership

1. **EODHD — account owner:** submit [the prepared support message](../2026-11-23-shutdown-recovery/EODHD-support-message.txt) and supply the invalid-bar evidence if requested. There are 408 invalid OHLC bars across five symbols in the retained provider responses. Do not waive validation or label these impossible periods. Latest market summary: 174 daily and 491 historical symbols with unresolved windows; 61 reviewed exclusions remain.
2. **SAM — optional owner confirmation:** check the account allowance or use [the prepared enquiry](../2026-11-23-shutdown-recovery/SAM-support-message.txt). Until confirmed, retain the conservative shared 10-request daily cap. No replacement key or increased spend is needed.
3. **Disclosure catchup — engineering:** the fresh monitor shows core collection running with progress at 17:47:39 UTC and no current prerequisite alert. Continue dependent catchup; do not treat all dates as complete.
4. **Publication — engineering:** finish active worker publication and verify new receipts. Today's successful audit reads already published data.
5. **Product search — engineering:** registry query hits MySQL's existing ten-second limit. EXPLAIN shows a large entity-name scan without an entity-type index. A simpler entity scan also timed out. Requires bounded selection or a reviewed index change; no database limit was raised and no live query was cancelled.
6. **Code backup — engineering:** selection includes a >10 MiB generated tokenizer at `sandbox/semiotic/hybrid-assets/assets/e5/tokenizer.json`. Review generated-asset exclusion; no file was removed or size safeguard disabled.

Intentional Reddit, Bluesky, GitHub data capture, Marketaux and NICE pauses remain. EDINET 2016 remains excluded. SMS is not an action item.

## Final monitoring reconciliation

The fresh health report at **17:53:48 UTC** has no inspection errors. The previously reported authenticated/ChiCTR/news service failures, daily audit staleness and publication missed-run conditions are absent. Core collection is running with recent committed progress. Market quality/coverage issues remain. A separate EDINET document-format issue is visible and needs exact-document investigation; it is not the owner-excluded 2016 archive requirement.

Worker detail also found a separate Health Canada daily invocation that timed out at 11:24 UTC. Its November 23 sample had passed; that does not clear today's timeout. This requires a bounded replay and fresh receipt before marking today's invocation recovered. Metadata workers and streaming metadata processing are active, not stopped.

The audit service finished successfully at 17:55:30 UTC; the independent health refresh finished at 17:55:55 UTC. Their saved evidence precedes any later queue completion.
