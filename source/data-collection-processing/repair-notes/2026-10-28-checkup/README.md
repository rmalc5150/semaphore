# October 28 checkup repairs

## Completed changes

- **FDA openFDA:** retain submissions with unknown action dates as explicit undated evidence, rather than aborting the entire application/window. Collapse identical duplicate submissions and retain distinct content variants with stable variant identifiers. Carry the evidence fields into normalized payloads.
- **FDA iRES:** accept the exact observed `412 / No results found` empty response; reject contradictory record counts and other malformed responses. This is an application response code, not a claim that all HTTP 412 errors are empty results.
- **NMPA regulatory publication:** project validated ISO timestamps to calendar dates for date-typed columns. Previously `date.fromisoformat` rejected timestamp values. Both failed source manifests now curate successfully with six records each. Raw observations retain the original timestamps.
- **SMS:** acknowledge the old alarm using the owner's October 28 confirmation of receipt. A later alarm state transition is still actionable. Deployed only the changed watchdog module with revision checking and a backup of the prior Lambda package. Refreshed monitoring without sending notifications.

## Verification and deployment

- `tests-final.log`: 71 tests passed, including the empty-response negative cases, FDA missing dates/variant identities and timestamp projection.
- `source-deployment.json` / `source-deployment-result.json`: historical worker SSM deployment succeeded, updating 447 module copies. Also updated 48 local daily-workspace copies. Deployment applies to subsequent processes, not already imported modules.
- `live-replays.json`: June 2016 FDA replay advanced to a bounded two-page limit and remains partial. January 2016 iRES modification-date query completed with zero results.
- `nmpa-curation-verification.json`: both previously failing NMPA manifests pass the repaired curator. This is not yet an Athena publication receipt. The publisher uses the updated local module on its next invocation.
- `sms-owner-confirmation.json`, `watchdog-deployment.json`, `monitor-current.json`: old SMS incident removed from active monitoring; no test text sent.
- `usgs-archive-probes.json`: candidate 2016–2018 archive paths returned 404; no guessed URL replacements deployed.

## Remaining work

1. Verify the two NMPA windows through the serialized publisher and Athena; finish and publish the repaired FDA windows. Do not mistake successful source replay or curation for Athena availability.
2. Reconcile worker S3 permission failures against exact resource keys (BLS/USGS enrichment prefixes are absent from the inspected artifact policy). No IAM policy was changed in this repair session.
3. Repair Zenodo requests, DataCite oversized scopes/pagination and preprint identity/provider failures; separately verify USGS historical archive URLs.
4. Resolve the remaining endpoint/access, daily pagination, market coverage, queue-wait and inspection issues listed in the refreshed status document.

Historical collection remains enabled. No service was paused or stopped during this repair session. Marketaux, Reddit, Bluesky, GitHub and NICE owner pauses were preserved. SMS is not an owner action item.

The [source status document](../../../data-source-status-2026-10-26.md) retains all 158 catalog entries and SQL links, ordered by attention required. Its older counts/previews are explicitly dated October 26; they are not presented as new October 28 measurements.
