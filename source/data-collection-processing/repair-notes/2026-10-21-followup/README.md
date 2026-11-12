# October 21 follow-up repairs

## Fixed and tested

- **HKEX spreadsheet filings:** both daily and historical failure evidence pointed to `.xlsx` originals passed to a text decoder. Added bounded workbook extraction with sheet names, cell coordinates, values and formulas. Original evidence remains intact. Unsupported ZIP files fail explicitly. Replayed the saved September 21 workbook: one sheet, 4,102 text characters, two retrieval chunks.
- **MHRA duplicate identities:** three designation IDs in the failed expired-register page also existed in previously committed current-register pages. Preserve expired-register assertions under distinct IDs; retain both source assertions rather than dropping a duplicate or asserting which register is correct. Current-register IDs remain stable. Replayed all 60 saved expired-register rows: 60 distinct IDs.
- **Reddit transient failures:** HTTP 500/502/503/504 now receive up to three total attempts with bounded backoff. Each attempt counts against the existing request budget. Access errors and quota failures are not automatically retried. Persistent errors remain failures; content revalidation/expiry behavior is unchanged.
- **Search scheduling:** both old weekly and configured daily timers were disabled. Enabled `optima-search-daily.timer`; the search service is now queued through its existing supervisor. Existing scope and USD 1 per-run cap remain in place.
- **OOM diagnosis:** added a source/job/window log immediately before each specialist capture. A killed process cannot write its normal failure receipt, so its preceding successful source must not be blamed for the memory failure.

Validation: 114 tests passed across disclosure collection/content, regulatory collection, Reddit, health repairs and S3 runtime. Changed modules also compile. `source-replays.json` records the saved-source replay results. These are parser/retry validations, not fresh production Athena receipts.

## Live status and limitations

- AWS SMS registration is **REVIEWING**. No further user action unless AWS requests changes. No test notification was sent.
- Daily collection has been queued to retry the repaired MHRA/HKEX paths. Search and Reddit are also queued. The common supervisor lock remains in place to protect shared runtime state.
- The supplied audit passed 85/85 shared Athena readbacks and 3,374 publisher receipt queries. This is evidence for already committed data, not proof of recovery after these new code changes.
- An authenticated daily worker was killed at 18:15 Madrid time by the aggregate data-slice memory limit. Its Python process had approximately 1.6 GiB anonymous memory. The last printed successful scope was SAM.gov; this does NOT identify the next failed source. The memory problem is not yet fixed. The new pre-capture log will identify the scope on its next scheduled attempt.
- Long worker queues, publication backlog, market coverage, source HTTP 400/403 errors, NMPA rendering, EIA workbook retrieval and unsupported historical designation dates remain unresolved. No gaps have been marked complete merely to clear alerts.

## What you need to do

1. Wait for the SMS registration decision. If AWS requests a change, share its exact feedback; do not keep changing the submitted URL while it is under review.
2. Optionally continue source-specific Athena checks for already published data. Report source, query ID and an example of a missing or unsuitable field.
3. No additional credential purchase or manual service restart is currently required from you. Remaining issues are engineering work, and queued repairs must still be verified from committed S3 output through Athena publication.
