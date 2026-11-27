# November 18 afternoon email repairs

Checked against the November 18, 15:35 CET overview. All times below are Europe/Madrid.

## Fixed and verified now

**Scheduled worker sleep was misreported as widespread service failure.** EC2 confirms M7 is stopped, and the controller records `phase=sleeping` with a safe-drain proof. Its snapshot naturally ages while the worker is off. Monitoring now recognises that bounded state as `scheduled_wait`, rather than emitting a missing-snapshot error for every service. It retains the previous invocation result, source reports and verified-data evidence, and does not claim current execution health. Progress-stall timing is suspended for those scheduled waits; independent source errors and unresolved prior execution failures remain. A missing drain proof, running/unexpectedly stopped worker, or expired maximum sleep interval does not receive this exception.

Live refresh: **zero inspection errors**, **23 jobs in scheduled wait**. The preview now groups active incidents under **13 services**, versus 26 in the email. These counts exclude the separate historical-gap groups. No email or SMS was manually sent. Normal notification scheduling remains unchanged.

**FDA Athena verification:** six of the 54 repaired windows now have verified publication receipts, up from three at the morning inspection. The three newly published windows contain **1,203 rows** (583 + 356 + 264), all with populated `data_json`. A fresh partition-bounded query succeeded, scanning **1,717,807 bytes**. Query ID: `cbd533f5-6c2f-434d-96ec-9fa41a4122d5`. Receipt checksums were also validated. See `fda-new-readback.json` and `FDA-new-windows.sql`. This is not a completeness claim for FDA history.

## Repaired in code, awaiting scheduled worker deployment

The real regulatory publication failure was AWS S3 **SlowDown**, saved at 13:26 CET in the worker's last research-publication report. Its generic queue scanner re-read all immutable historical queue entries on every run, even though most were already published.

`window_publication.py` now limits ordinary regulatory scans to **128 queue candidates**, carries a conditional continuation cursor, rotates through the archive, and reduces concurrent metadata reads from eight to four. It retains receipt-checksum verification, publication limits, failed inputs, and queue objects. A candidate beyond the current publication budget is not skipped by the cursor. Explicitly targeted repairs and specialist duplicate-alias checks keep their existing behaviour.

**Deployment is pending, not verified live.** SSM rejects a command addressed to the stopped instance (`InvalidInstanceId`); no worker start was requested. A bounded controller timer, `optima-publication-repair-install-20261118.timer`, checks every five minutes and submits the narrow patch only once the worker is normally running and SSM is online. It stops after installation, failure, or 25 hours. The installer preserves other worker edits, requires exact replacement anchors, backs up the existing files, compiles before atomic replacement, and writes an S3 deployment receipt. The staged transformation was checked for AST equivalence with tested code.

Inspect `publication-deployment-state.json` and, once available, `publication-deployment-result.json`. The worker receipt is:

`s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/repairs/2026-11-18-afternoon/publication-deployment-result.json`

This patch bounds the known oversized metadata scan; sustained publication and recovery from throttling still need verification after it is installed. **48 FDA windows and the newly repaired ClinicalTrials scope lack publication receipts.** They are retained in the existing queues. Earlier captured PortWatch scopes likewise require their own publication/readback before being declared Athena-ready.

## Next session and remaining repairs

M7 stopped at **13:50 CET November 18**. Under the existing policy, its earliest threshold-based wake is **03:50 CET November 19**; pending work triggers a wake by **13:50 CET November 19**. The earlier wake additionally depends on the configured metadata queue threshold. There are **27 durable service requests** queued. These are policy bounds, not predicted completion times. The worker was intentionally left asleep to preserve the configured cost limits.

Remaining service work includes old execution failures without enough recovery proof; provider 429s; HKEX/disclosure prerequisites; market mappings and evidenced price-window exclusions; Finlight pagination consistency; and publication/readback. Historical source groups still include Zenodo, PortWatch, MHRA, DataCite, CTIS, WTO, USAspending, preprints, NHSBSA, UNIDO and Copernicus. No historical gap was waived just because a process succeeded or because its data might be unavailable.

The morning ClinicalTrials window remains captured and queued, not Athena-verified. The MHRA current-list date limitation, existing raw-validation holds and original historical failure evidence remain documented. EDINET 2016 remains excluded. Reddit, Bluesky, GitHub source capture and Marketaux remain paused. The approved residential PDF fallback cap remains four attempts/day shared across its named sources. SMS is working.

## Owner action

No new API key, licence purchase, IAM change or manual restart is requested by this checkup. You can inspect the newly verified FDA windows using `FDA-new-windows.sql` or `FDA-random-sample.sql`, and report missing specialist fields. The worker deployment and remaining repairs are engineering work; they do not require you to rerun commands.

## Tests and evidence

**79 relevant tests passed**, including proof-bounded sleep, unexpected/overdue-state rejection, source-error retention, queue continuation/wraparound, and not skipping the next unpublished window. See `tests.log`. Saved S3 snapshots, publication receipts, query results, current incident state and the corrected overview preview are alongside this document. `health-refresh.log` records health/incident refresh with notifications disabled.
