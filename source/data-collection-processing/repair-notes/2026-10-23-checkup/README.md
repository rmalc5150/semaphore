# October 23 checkup repairs

This report addresses the supplied 24-hour checkup. A successful bounded replay is not a completed archive. Evidence and individual logs are retained in this directory.

## Repairs and verification

| Checkup item | What changed / verified | What remains |
|---|---|---|
| HKEX unsupported ZIP | Added bounded DOCX text extraction, including tables. Replayed September 22 and January 2021 scopes beyond their failed pages. | Remaining pages and dependent disclosure extraction continue; no full-window completion claim. |
| HKEX non-PDF response | The saved response was an official issuer-removal notice. Preserve listing metadata and the notice with `publisher_removed` status, exclude notice text from event classification, and continue. September 24 and September 28 replays succeeded. | September 28’s additional page is committed to S3; the normal Athena publisher has been explicitly queued under the shared lock. Its readback is still pending. Removed original content remains unavailable; this is not successful original-document capture. |
| ClinicalTrials.gov HTTP 400 | Provider explicitly reported an invalidated pagination token. Added bounded refresh handling; replay committed 200 records in a new snapshot. | February 2021 window remains partial; prior snapshot records are retained. |
| NIH split-count failure | Fixed an exclusive end-date boundary error that omitted 110 records during partition planning. Fresh split totals reconcile; 500 records committed. | Continue the remaining pages with count and duplicate checks intact. |
| NMPA scraping 429 | A live retry fetched and validated page 1240, committing cursor 1241 without a 429. Existing inventory contains 24,462 unique records; this page contained already-seen identifiers and added zero new unique records. | Inventory is incomplete; successful navigation is not proof of complete detail capture. |
| CAISO / specialist historical crash | Converted provider error text into a valid stable reason code, preventing a secondary exception that aborted the whole scheduler. Corrected the rolling API-retention boundary so it does not round back to an expired month start. | Missing older prices require the archive route; dedicated archive/API boundary reconciliation remains necessary. No unavailable prices were invented. |
| Shared-lock queue timeouts | Reduced batches for collection daily, specialist daily/historical, authenticated daily/historical, research publication and specialist publication. Locks, quotas and memory limits are retained. | Measure waiting times and committed progress over subsequent uninterrupted cycles; this is not yet proof that the backlog is shrinking. |
| Athena publication | Two publication passes verified all indexed batches, including the repaired HKEX, ClinicalTrials and NIH batches. Latest total: 16,868,971 physical observations across 86 source/dataset partitions. | This includes retained versions and partial scopes, not unique entities or complete history. Typed specialist transformations remain separate. |
| Daily audit | Reran successfully: 86 shared-table readbacks; 24 manifests and 3,601 S3 objects checked; 3,768 receipt queries checked; no query, S3 or receipt-query failures. | The audit confirms storage/readback, not field-level specialist fitness for every record. |
| Paused Reddit / Bluesky alerts | Monitoring now recognizes explicit owner pauses and excludes them from operational incident evaluation; AWS watchdog code deployed and checksum verified. | Reddit, Bluesky, GitHub and Marketaux remain paused until requested otherwise. |
| Old source-failure alerts | Monitoring now accepts only newer, same-task, checkpoint-verified outcomes to supersede these specific stale failure reports. Failed scope outcomes were reconciled without advancing date watermarks. | Unrepaired scopes and unmet prerequisites remain visible. |
| Patent access | Application 16545140 remains the previously authorized, verified metadata-only exception. | Source-change recovery and other patent windows remain subject to their cooldowns and actual successful checkpoints. |
| Maintenance exits / publication service failures | Retained journals distinguish maintenance SIGINT/KeyboardInterrupt from the CAISO software exception. Completed repair jobs have individual exit results and durable checkpoints. | A maintenance interruption is not an OOM. Later service success must still be verified; do not blanket-reset failed units. |
| Market gaps | No unsupported exclusions added. Last reviewed counts: 174 daily / 202 historical symbols unresolved, 46 reviewed window exclusions. | Review listing/ticker/trading dates and replay real gaps. |
| MHRA historical designation dates | Retained explicit missing-date limitation. | Dated original evidence is needed; retrieval or expiry dates are not substitutes. |
| SMS | All five AWS alarms were OK; US toll-free registration version 3 still `REVIEWING`. No test messages sent. | AWS approval and positive delivery evidence remain outstanding; an OK alarm alone is not proof. |

CAISO directs data older than 39 months to its [historical download route](https://oasis.prod.caiso.com/mrioasis/logon.do). The expired standard-API slice is a coverage gap, not an accepted empty result.

## Athena verification evidence

Use workgroup `optima-collected-data`. Representative payloads were read through bounded verification partitions and saved as `*-samples.json`.

| Source | New records verified | Count query | Sample query |
|---|---:|---|---|
| HKEX filings | 300 | `8c01f158-c859-42e9-8858-778a9d7894eb` | `b3c3436a-c6a8-4b9e-a7b0-0db571ce433a` |
| ClinicalTrials.gov | 200 | `7eea87df-7836-42ca-af18-d388ac81eae4` | `4e54d570-fa14-4fc1-b6b2-6944eb56f790` |
| NIH RePORTER | 500 | `826aeb53-2601-49fd-bc5c-1df02eb93066` | `6d92b189-58cf-405f-b1b9-23442e69fc3e` |

Samples contain provider identifiers, dates/provenance and substantive payloads: HKEX listing and capture metadata, ClinicalTrials protocol sections, and NIH award/project fields. Candidate entity links and historical-availability limitations remain explicit.

## What you need to do

1. **Review sampled data in Athena.** Open the sample query IDs above, inspect the JSON fields and decide whether the dates, identity links and substantive fields meet your specialist requirements. Report a source, query ID, record ID and the missing/incorrect field.
2. **Check AWS SMS registration.** Open the US toll-free registration, inspect version 3, and respond only if AWS requests corrections or additional information. No replacement API keys or purchases are needed for the fixes above.

Engineering owns the remaining coverage reviews, prerequisite completion, archive routing, publication continuation and queue measurements. These are not requests for you to debug code.

## Operational checks

Every timer matched its pre-repair enabled/active state after restoration (`timer-verification.json`); intentional pauses were preserved. No notifications were sent by the repair runs. Regression verification: 155 tests passed using the checksum-validated archived universe fixture, without modifying RAM-backed production configuration.

Evidence: `summary.json`, `nih-boundary-counts.json`, `nih-boundary-replay.json`, `outcome-reconciliation.json`, `athena.log`, `athena-final.log`, `sample-verification.json`, `health-final.json`, `schedule-changes.json`, `watchdog-deployment.json`, `final-tests.log`.

## Final monitoring snapshot

At 09:11 UTC the health export had no inspection errors. Current source issues were disclosure prerequisites, unresolved market coverage, patent source-change recovery, a retained specialist maintenance interruption, and unavailable MHRA historical dates. The repaired HKEX parser/non-PDF, ClinicalTrials HTTP 400, NIH split-count and NMPA 429 issues were absent from current source issues. The watchdog still retained 31 incidents overall, including service failures awaiting later verified execution; this is not an all-clear. See `health-final.json` and `watchdog-final.json` rather than treating the repair summary as zero remaining incidents.
