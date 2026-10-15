September 24 cutover: scheduled global patent backfill now starts 2021-01-01
with separate collection/publication checkpoints and unchanged shared query
budgets. January–April 2015 remain published (164,690 records). All migrated historical
collector defaults now start 2021-01-01, superseding the patent-only cutover. HMM/TFT intended start is 2021-01-01; coverage and
point-in-time eligibility still require validation. See HISTORICAL_COLLECTION.md
and PATENT_BACKFILL_OPERATIONS.md. Earlier activation details below are historical.

# Global patent coverage and proposed backfill

Verified September 23, 2026 against the source revision published at 17:59:58 UTC.
The query covered all 173,516,400 rows across 107 patent authority codes, including
regional and historical authorities. Source metadata was unchanged before and
after execution; grouped counts matched the table count. This is a source-wide
inventory, not a sector-filtered count or a count of distinct inventions.

| Authority | Latest observed publication | Lag on September 23 | Publications in trailing 90-day interval |
|---|---|---:|---:|
| China (CN) | 2026-09-08 | 15 days | 995,268 |
| United States (US) | 2026-09-17 | 6 days | 197,616 |
| European Patent Office (EP) | 2026-09-16 | 7 days | 87,737 |
| Japan (JP) | 2026-09-04 | 19 days | 89,198 |
| South Korea (KR) | 2026-08-31 | 23 days | 64,913 |
| WIPO (WO) | 2026-09-03 | 20 days | 56,896 |

These maxima do not establish complete coverage through the dates shown. The
source is fresher than the April dates measured on September 22, but still does
not provide same-day worldwide coverage. Other authorities have much older
latest observations; see the full CSV. The trailing interval includes both
endpoints: as-of minus 90 days through as-of.

The source contains 1,221,764 records with missing/invalid publication dates and
211 with dates after the as-of date. Missing-date records cannot enter the
date-filtered backfill. They require a separately labeled undated discovery
cohort, without invented publication dates or model availability timestamps.
These counts cover all sectors. Historical aliases, legal-company matches and
technology classifications remain subject to the established review rules.

Evidence:

- [All-authority CSV](unused/reports/patent-source-coverage-2026-09-23.csv)
- [Coverage report, query and statistics](unused/reports/patent-source-coverage-2026-09-23.json)
- [Current-universe extraction dry run](unused/reports/patent-bigquery-access-v0.3-2026-09-23.json)
- S3: `s3://data-collection-059416028963-us-east-1-an/research-data/operations/patents/source-coverage/d566ba358400cdb3e644398ce8b9cde6304ea6eda9ace82ec4ef655c51349cbb/result.json`

The coverage query billed 2,082,471,936 bytes, approximately $0.012 at the US
on-demand rate before free usage. Its enforced ceiling was 5 GB. A repeated live
check read back the completed S3 result rather than executing another data query.

The current-universe January extraction dry run estimates 47,135,127,425 bytes,
about $0.27 before free usage; it still fits the 50 GB ceiling, approximately
$0.284 per query. That extraction was estimated only, not executed in this step.
The source is not partitioned or clustered: shorter date windows should not be
assumed to reduce scanned bytes. Every actual window requires a fresh dry run.

## Proposed historical execution

The user selected **January 1, 2015** on September 24 for all historical data
capture. The shared setting is `config/historical-collection.json`; see
HISTORICAL_COLLECTION.md. The selected plan is
`unused/reports/patent-backfill-selected-2015-2026-09-24.json`, with end-exclusive
September 23, 2026. The earlier alternative proposals remain archived:

| Start-date option | Monthly windows | Reservation for one 50 GB-capped query per window |
|---|---:|---:|
| January 1, 2015 | 141 | $40.07 |
| January 1, 2000 | 321 | $91.23 |
| All dated source history, starting July 4, 1782 | 2,931 | $833.04 |

These are conservative query-analysis reservations for the proposed monthly
layout, before free allowances. They are not total project quotes or enforced
account-level spending caps. They exclude S3, EC2, transfer, later revisions and
replacement jobs after result expiry. The earliest parsed date is a source
observation, not independently verified historical completeness. An all-history
request should use coarser windows for sparse older periods after volume review;
it need not incur 2,931 separate monthly scans.

Proposal files are `reports/patent-backfill-proposal-*-2026-09-23.json`. The
offline `patent_backfill_plan.py` validates that coverage and cost evidence use
the same source revision and generates exact, exclusive monthly boundaries.
It does not submit jobs, change collectors or enable a timer.

Execution steps for the selected range:

1. Generate window-specific queries with universe 0.3.0 and all four sectors'
   technology rules. Record the observed source revision and dry-run estimate.
2. Submit one bounded job, retain its job ID, and finish downloading its result
   pages to S3 before submitting the next window. Partial results cannot advance
   completed coverage. Keep daily USPTO collection independent.
3. Resume the same job after interruptions. Temporary BigQuery results are
   normally retained for approximately 24 hours and may expire earlier. If they
   expire, stop for review instead of silently submitting another billed job.
4. Review and curate complete manifests into versioned Athena releases. Preserve
   raw evidence, unresolved company relationships and explicit coverage gaps.
5. On later source revisions, reconcile recent periods and plan periodic older
   history comparisons: corrections can change records outside a recent window.

The bounded backfill scheduler is now implemented and enabled; January 2015 is
complete with 37,738 candidates and verified S3 evidence. See
[PATENT_BACKFILL_OPERATIONS.md](PATENT_BACKFILL_OPERATIONS.md) for limits,
resume behavior and status commands. Automatic incremental Athena publication
is **enabled**, checking completed months every ten minutes with an independent
verified-publication cursor and retry path. January 2015 is published through four new
monthly backfill views; see [PATENT_BACKFILL_ATHENA.md](PATENT_BACKFILL_ATHENA.md).
The current reviewed January 2025 Athena pilot remains unchanged.
Source-wide coverage reports are stored in S3 and local JSON/CSV; they are not
yet a new Athena table.

Validation: 92 tests across coverage, backfill planning, patent operations,
collectors, shared storage and BigQuery access; live capped coverage execution,
metadata/count reconciliation, extraction dry-run and S3 result-reuse check.

References: [BigQuery pricing](https://cloud.google.com/bigquery/pricing) and
[temporary cached results](https://docs.cloud.google.com/bigquery/docs/cached-results).

## Additional US examination and petition history

The current shared historical configuration starts January 1, 2021 and supersedes the older January 2015 selection described above. Office Actions and final Petition Decisions require separate historical tasks and coverage receipts; completed publication/application windows cannot stand in for their history. Partition by documented action/decision date, including in-range documents for older applications where supported. Preserve unknown availability and source coverage gaps. See [USPTO examination and petition rollout](USPTO_PROSECUTION_ROLLOUT_PLAN.md) for the backfill, incremental overlap and acceptance gates. The source adapters and hourly bounded scheduler are now implemented; see [execution status](PATENT_PROSECUTION_OPERATIONS.md). Existing global backfill checkpoints are retained.
