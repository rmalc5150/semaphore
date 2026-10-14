# Live coverage reconciliation — September 25, 2026

The live S3 audit ran from 05:53:18 to 05:54:59 UTC while scheduled collectors
continued. It was read-only and ran under a 128 MiB service cap inside the
shared data-job slice. This is an individually timestamped scan, not an atomic
snapshot of the entire platform.

## Checks completed

- Read 3,185 task heads and their committed terminal histories; checked task
  identities, source scopes, manifest counts and completion/exhaustion markers.
  Earlier complete versions remain visible when a later refresh fails.
- Listed 6,553 raw objects and compared committed manifest references against
  object existence and byte size. Objects arriving after the initial listing
  were checked individually. No metadata inconsistencies or missing/size-mismatched
  referenced objects were found. Active unfinalized attempts are not completed coverage.
- Checked 1,364 live window-publication receipts against the hashes and release
  identities of their stored verification records. Separately verified four
  monthly patent publication receipts. No receipt mismatches were found.
- Read and hashed the oldest/newest successful nonempty batch sample per
  source/dataset, covering 26 pairs and 6,612 sampled record observations.
  All sampled batch hashes/counts matched. This does not hash every raw byte;
  oldest/newest selections can overlap and are not a unique-record total.
- Queried the live Glue catalog: nine configured databases were accessible.
  The social database lookup failed and has no verified publication here.
  These are catalog checks, not new Athena count scans.

## Findings requiring action

| Area | Finding | Required follow-up |
|---|---|---|
| Market prices/actions | All 492 configured symbols still have missing requested intervals from January 2021 through September 24, 2026; 60 have no completed window. | Continue backfill and adjudicate empty-price windows against listing/IPO/delisting dates. An uncollected pre-listing interval is not automatically a provider failure. |
| Market publication | 2,318 complete market task heads versus 1,144 matching active publication manifests in this snapshot. | Drain and reconcile publication queues. These are different task/receipt counts, not a claim that their difference equals missing rows or partitions. |
| News | Current configured historical Marketaux sector queries have complete requests through January 4, 2021; the remaining historical request range is missing. Daily query/configuration scopes are separate. | Continue bounded history; inspect page limits, quota failures and Finlight response-shape failures. Sector searches do not guarantee coverage of every tracked company. |
| Patents | Completed raw windows and older reviewed samples exist; four verified monthly publication receipts cover the retained 2015 history. | Reconcile the 2021 collection stream and its publication separately; do not count the retained 2015 months toward the 2021 requirement. Query-plan/export scopes remain separate. |
| Regulatory | NMPA inventory remains partial; bounded trial cohorts exist. Several regulatory adapters represent current lists or snapshots. | Complete source-specific baselines and establish historical-version contracts. A requested 2021 date does not turn a current list into a 2021 snapshot. |
| Personnel | 88 completed archive task heads and 88 matching publication manifests in this snapshot. | Continue parent news/filing backfills and candidate review. This is not exhaustive personnel-event coverage. |
| Reddit | No committed migrated collection found; the legacy connector's required client ID/secret environment variables are absent from the audited process. | Establish an authorized access path and verify historical depth. This does not rule out credentials in another store. No authenticated request was attempted without credentials. |
| Search rankings | No configured provider/history contract or committed collection found. | Select and verify a historical ranking source, queries, domains, countries, engines and sampling interval. Required company/date ranges are recorded as uncollected. |
| Historical usability | None of the 6,612 sampled records has a populated `available_at`. | Verify original field availability, revisions, identity and historical watchlist membership before using these records as historical model inputs. Null availability does not prove that a record can never become usable. |

## Exact gap files and interpretation

[Query/date gaps](reports/live-coverage/query-date-gaps.csv) identifies each
company symbol or exact query scope, its universe hash, required interval and
missing collection/publication intervals. Boundaries are UTC and end-exclusive.
[Full reconciliation](reports/live-coverage/reconciliation.json) includes the
completed intervals, attempt manifests, failure reasons, source-success times
and raw-sample checks behind those calculations.

The current configured market and news query sets are explicitly seeded, so a
never-attempted symbol or query cannot disappear from the report. Each enabled
company also has a required Reddit and search-ranking entry, even though the
provider/query contracts remain unresolved. Company eligibility remains
provisional and all markets are in scope.

Different universe hashes and query parameters are not silently merged.
Historical and daily news configurations use their respective configured
requirements. Other observed query scopes retain provisional requested-history
requirements; they do not certify an exhaustive set of required queries.
Snapshot and parent-cohort sources have unknown historical gaps rather than
misleading interval complements. Patent export/query-plan scopes require
separate operational reconciliation before aggregation across months.

A missing interval means no committed complete request was found under that
contract. It does not mean no events occurred, that the company existed for
that entire interval, or that the provider can supply the missing history.
Publication gaps reflect the active receipt paths inspected; older pilot
publication can exist outside those paths. See the local release receipts in
the main register as well.

## Access and remaining validation

Recorded successful collection times and failure reasons are refreshed from
live manifests. Paid provider requests were not replayed or budgets increased.
Recent success verifies access at that run time; it does not establish an
account's historical entitlement or continuing availability. Old successes,
blocked sources and missing credentials remain explicit access-verification
work. [Access/catalog checks](reports/live-coverage/access-catalog.json) records
the separate live Glue check and credential-presence result without secrets.

The refreshed [source register](SOURCE_COVERAGE_REGISTER.md) contains live head
statuses, complete-version counts, last successful collection, failure reasons,
gap-report links and catalog results. Source requirements now also include the
previously omitted USPTO assignment and NMPA inventory datasets.

Refresh sequence: run `coverage_live_snapshot.py` through an equivalent capped
service (it also refreshes patent receipts and the catalog access snapshot),
then run `reconcile_coverage.py` and `source_coverage_register.py`. Interval tests
cover overlap, clipping, exclusive boundaries, empty coverage and timezone
normalization. No collection checkpoints or publication state were modified.
