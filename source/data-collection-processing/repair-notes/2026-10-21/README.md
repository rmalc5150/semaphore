# October 21 pipeline repairs and remaining actions

Evidence checked October 21, 2026, approximately 05:30 UTC. The supplied alert was dated October 20. This report distinguishes deployed fixes, verified recovery and unresolved work.

## Repairs completed

- **Independent health monitoring:** removed the collection-workspace supervisor lock from `optima-collection-health.service`. Deployed the systemd override and preserved it in the runtime installer. Monitoring reads durable S3 evidence and cannot write to the collection workspace. The service finished successfully at 05:20:30 UTC; its timer remains active. The 05:19:46 UTC snapshot has no inspection errors (see `health-after.json`).
- **Queue status:** all services are checked for actual worker processes. A service waiting on the new outer runtime lock is reported as queued, including jobs formerly configured as nonserialized.
- **Search publication verification:** reads the checksum-verified publication pointer from the durable S3 runtime index instead of requiring an evictable RAM report. Existing publication receipt, Athena result and Parquet checksum checks remain required.
- **USPTO request gate:** atomic state updates now target the hydrated RAM file, with an allowed temporary JSON filename, preserving the root symlink and persisted rate-limit reservation. This addresses a concrete incompatibility with the new runtime. The patent daily worker is still queued: live patent recovery is NOT yet verified.
- **Validation:** 50 tests passed across `test_s3_runtime`, `test_collection_health_repairs`, `test_collection_alerts` and `test_monitoring_overview`. Regression tests cover the USPTO symlink/state reservation, queued processes and search-pointer checksum rejection.

## Verified recovery, not new repairs in this session

- Root disk has 19 GB available (39% used). The previous disk cleanup/S3 runtime migration had already taken place before this investigation. Old disk-full incidents are not proof that disk remains full.
- `optima-committed-athena.service` completed at approximately 04:45 UTC: **85 partitions / 15,747,951 records verified**, followed by a verified S3 state checkpoint. This confirms access to committed batches, not full historical coverage or specialist feature readiness.
- Specialist publication completed another successful run and verified its S3 checkpoint at 05:22:50 UTC. This does not clear its entire backlog.

## What you need to do: SMS registration

1. Open AWS **End User Messaging SMS** in **us-east-1** and open **Registrations**.
2. Select `registration-3ebe8dc67b2b4cc29bbaf6d5847a3257` and review version 2. Its current rejection is **Invalid Website URL — Invalid or inaccessible website URL**. Version 1's opt-in rejection is older.
3. The submitted website is `https://optima-holdings.com`. It currently returns HTTP 200 after redirecting to `https://www.optima-holdings.com/` from EC2. Check the final address yourself in a private browser window without logging in. Confirm it accurately identifies your business and that the registration's supporting pages are accessible.
4. Edit/resubmit the registration with the working canonical address and accurate details. If AWS still rejects it, open an AWS Support case with the registration ID, rejection text and evidence that the site is publicly accessible; ask what specifically is inaccessible to their reviewer. Changing the URL alone does not guarantee approval.
5. After approval, verify that the sending number is active and that the next scheduled notification has successful delivery evidence. No test SMS was sent during this repair session.

No new API purchase or credential replacement is justified by the evidence gathered in this session.

## Outstanding engineering work — not tasks for you to perform manually

| Area | Current finding | Work required before calling it fixed |
|---|---|---|
| Shared runtime queue | Many jobs wait on a single supervisor lock; monitoring is now independent | Measure worker throughput and fairness; bound long jobs or redesign isolated workspaces safely. A queued timer is not proof of a completed capture. |
| Patent daily | Previous collector exception was PermissionError; request-gate defect corrected | Verify next bounded live capture, durable checkpoint and Athena publication. |
| Core history | Record limit, HTTP 400, missing historical designation dates and HKEX text-decoding failure | Inspect exact failed scopes/responses; repair requests/pagination/document decoding. Preserve unsupported dates as coverage gaps. The HKEX failure currently carries a misleading EDINET-named decoder error. |
| Market | 179 daily / 208 historical unresolved symbols; 26 reviewed exclusions | Verify ticker/listing/date evidence, repair mappings and add only supported window exclusions. Counts overlap; do not add them as unique companies. |
| Daily collection | Duplicate provider record and prerequisite failure | Inspect conflicting identities and upstream manifests; do not silently drop conflicting records. |
| Patent prosecution and social | HTTP 403 | Inspect provider-specific denial responses and endpoint/access requirements before asking for new credentials. |
| Specialist inputs | EIA HTML instead of workbook; saved failures also include TED oversized records, NIH and other source-specific issues | Repair source adapters and replay failed scopes. Preserve full source evidence; do not truncate oversized TED records merely to pass storage limits. |
| Publication | New runs succeed, but backlog remains | Continue publication and verify each affected source in its intended Athena table; a shared-table count is not sufficient for every specialist route. |

Do not mark yesterday's entire list recovered based on these successes. Individual failed scopes still require committed output and verified publication. Keep existing scheduled workers running; repeatedly restarting queued jobs will not add capacity.

## Optional review you can do now

Use the existing `SQL-checks.md` source-specific queries to inspect already published data. Check identifiers, event dates, units and payload fields needed for the specialist layers. Record the source, query ID and a sample record when something looks wrong. This is semantic review; it does not replace the remaining engineering repairs above.
