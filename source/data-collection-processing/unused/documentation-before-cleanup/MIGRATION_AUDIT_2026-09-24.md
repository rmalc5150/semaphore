Superseded rollout items: news automation and market price/split/dividend migration are now implemented and scheduled. IBKR is excluded. See NEWS_AUTOMATION.md, MARKET_COLLECTION.md and EODHD_QUOTA.md for active operation and limits. This file retains the earlier audit findings as history.

# Migration and Athena audit — September 24, 2026

All migrated historical defaults are January 1, 2021. This is a requested
collection boundary, not evidence of complete coverage from that date.

Verification: inspected collector implementations, active configuration, installed
systemd commands, local release/verification receipts and the live Glue catalog
in us-east-1. The six configured project databases contain 49 external tables
and four views. Catalog presence was checked live; this audit did not rerun all
Athena data scans or revalidate every provider. No collector or schedule was launched.
See `reports/migration-athena-catalog-audit-2026-09-24.json` for catalog evidence.

| Dataset / source | Verified implementation and Athena state | Remaining work |
|---|---|---|
| HKEX daily/historical prices and foreign cross-listing prices | Legacy CSV/S3 scripts; foreign-listing enrichment uses Yahoo chart data. No price tables in the six project databases. | Shared raw evidence, listing IDs, date/currency/calendar handling, bounded 2021 backfill, daily catch-up, reviewed mappings and Athena publication. |
| Corporate actions | No dedicated migrated action collector or project Athena tables found. | Implement split/dividend and other required action ingestion, effective dates, adjustment factors and reconciliation; publish with price data. |
| People / workforce movements | Legacy public RSS, date-bounded news search and JSONL imports. No project Athena tables. | Shared company/person IDs, evidence, dated employment events, coverage-aware 2021 history, recurring collection, review and publication; broaden beyond biotech. |
| Conferences / abstracts / presentations | Legacy Crossref proceedings metadata collector. No project Athena tables. | Shared ingestion, company/product links, explicit event/publication dates, broader sector coverage, source limits and Athena publication. Full abstracts and acceptance dates are not always present in existing source data. |
| Social mentions | Legacy Reddit, Bluesky, YouTube and authorized JSONL imports. No project Athena tables. | Shared evidence/checkpoints, timestamped engagement revisions, source-specific history validation, scheduling and publication. Do not claim an archive back to 2021 without evidence. |
| Finlight / Marketaux news | Shared migration and four live Athena tables; verified September 23 daily cohort. | Recurring daily catch-up/reconciliation and incremental publication. January 1, 2021 Marketaux pilot has 44 observations in S3, not yet published. Use the observed-archive config for Marketaux; default config still labels its history unverified. Finlight configured plan is recent-only. |
| Clinical/regulatory: ClinicalTrials.gov, FDA, EMA/CTIS, MHRA, Japan, ChiCTR, NMPA | Shared adapters and nine regulatory Athena tables; all seven sources represented in a bounded release. | Full 2021-onward coverage, current-version versus historical-version handling, recurring publication. Complete/validate NMPA inventory then detail cohorts and changed-record reconciliation; validate dedicated ChiCTR scheduling. One NMPA trial in the pilot does not establish registry coverage. |
| SEC and HKEX disclosures, documents, PR, licensing, M&A, strategic transactions | Shared migration, daily orchestration, six SEC tables and five disclosure tables. | Historical backfill and recurring curated publication, controlled universe updates, unreadable-document handling, additional regional/IR discovery. Transaction candidates still need entity/product/date review; standalone news-derived discovery is not equivalent to disclosure-derived coverage. |
| EODHD, company universe and registry reviews | Scheduled profile collection and 15 live research/review/universe tables. | Continue profile collection, resolve identity/sector conflicts, build private-company discovery beyond a queue, and publish reviewed new cohorts. September 24's 7,900-record cohort manifest is absent from the pinned research-release input config. Existing 9,438-profile coverage figures describe a published snapshot, not all currently collected S3 data. |
| Global patents / USPTO / assignments | Migrated; 10 tables and four views. Separate USPTO daily, global metadata monitor, monthly backfill and publication timers exist. | Finish 2021-onward backfill, current global daily ingestion/reconciliation, broader identity and ownership review, assignment coverage. Metadata monitoring alone does not ingest current global publications. Preserve older verified monthly releases. |
| Company/product/person relationships and partnerships | ID contract, candidate events and some patent/receipt relationships exist. No complete shared product/person/relationship dataset found. | Curate dated supported links across trials, patents, disclosures, licensing and employment; publish reusable relationship tables with evidence and unresolved status. This is partly curation/integration, not a wholly separate source migration. |

Priority based on the remaining project dependencies:
1. Finish news scheduling/publication, including the collected 2021 pilot.
2. Migrate prices and corporate actions, which are required for model targets and adjustments.
3. Close regulatory baseline gaps and publish new SEC/regulatory/disclosure/EODHD cohorts.
4. Migrate people, conferences and social; expand relationship and private-company coverage.
5. Continue the bounded patent backfill and identity/ownership review in parallel with those workstreams.

Across groups: distinguish raw S3 collection from reviewed, query-verified Athena
publication; retain partial/failure states, source coverage and observation times.
HMM/TFT feature tables, point-in-time eligibility enforcement and RDS prediction
integration remain downstream work, not completed source migrations.

Some older status strings are stale: patents do have dedicated scheduling;
Finlight/Marketaux are migrated; the full shared historical default is now 2021.
This dated audit supersedes those strings without changing checkpoint config hashes.
