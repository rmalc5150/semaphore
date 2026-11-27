# EDINET 2016 — excluded by owner

On November 16, 2026, the owner confirmed that the EDINET 2016 archive is not essential and must not be treated as an alert.

Applied a permanent, explicit historical-scope exclusion for `edinet_filings`, adapter `edinet`, covering **[2016-01-01, 2017-01-01)**. Matching requests return an accepted owner exception before any provider call. The historical-gap auditor uses the same rule, so old failure receipts for these scopes do not become actionable alerts. No data completeness is claimed.

The current cached gap report was updated conditionally, after archiving its original bytes. **Four intersecting gap intervals were removed or trimmed; readback confirmed zero remaining EDINET 2016 gap intervals.** The 459 other gap intervals were retained. Any portion outside 2016 remains eligible for alerts. See `verification.json`.

Deployed the reviewed policy to **155 runtime files**, with backups and checksums. Boundary tests confirmed that 2017 requests and daily capture remain in scope. **17 focused tests passed**, including proof that excluded historical requests do not call EDINET and do not produce a false complete-data manifest.

Removed the alternative-archive acquisition task from the current owner checklist in `data-source-status-2026-10-26.md` and the preceding checkup notes. Existing saved records and original failure evidence remain retained. No collection timers were stopped and no notification was sent manually.

Owner decision: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/repairs/2026-11-16-edinet-scope/owner-decision.json`.
