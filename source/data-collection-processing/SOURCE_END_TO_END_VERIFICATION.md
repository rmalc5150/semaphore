# Source verification and remaining blockers

September 25, 2026. The verification matrix is in
[reports/source-end-to-end-verification.json](reports/source-end-to-end-verification.json).
Each required source has separate access, pagination/totals, checkpoint/recovery,
revision/duplicate, raw-read-back, publication/query and history status.

## Completed verification

- The capped source contract suite passed **257 tests**, covering source
  pagination, totals, source changes, failed/partial completion, checkpoints,
  recovery, immutable revisions, duplicates and publication failure/retry paths.
- A further targeted 42-test run passed after the universe cutover and personnel
  changes. Suites overlap; these counts must not be added as unique tests.
- Fresh Athena count checks matched the expected tables for **22 source/dataset
  pairs**, using bounded published partitions and existing 100 MiB query caps.
- Additional live queries succeeded for listing inventory/profile and separate
  patent/assignment tables. Counts are in the linked receipts, not assertions
  of full historical coverage.
- Live S3 checkpoint/manifest audit and raw read-back results are preserved in
  [COVERAGE_RECONCILIATION.md](COVERAGE_RECONCILIATION.md). Full raw-byte hashes
  were sampled, not exhaustively reread. Production collectors were not
  deliberately interrupted; recovery was exercised with test stores/fixtures.
- Nine people feeds now have successful source captures. Three newly added
  feeds yielded 95 articles, all now published and Athena-count-verified.
  Receipts: `reports/personnel-new-feed-publication.json`.
- Official business sources and 20 registry identifier lookups were captured
  with source hashes. Universe 0.5, its admission ledger and eight universe
  tables were published and query-verified.

## Explicitly incomplete or blocked

- Reddit: historical/API access is not configured in the audited environment.
  Search rankings: provider/query/history contract not yet selected or verified.
  These required sources are not marked as successful empty datasets.
- Bluesky: recorded HTTP 403 failures; not a substitute for Reddit coverage.
- NMPA inventory: partial/rendered-source failures; a verified small trial cohort
  does not establish the baseline. ChiCTR recurring/history coverage remains
  limited despite a queryable cohort.
- Finlight has recent-only configured access. Marketaux has bounded observed
  archive access, not exhaustive 2021–present company coverage. Quota/page and
  response-shape failures remain explicit in the live register.
- Market empty-price windows need listing-date and source investigation.
  Prices, splits and dividends do not cover every corporate-action type.
- Patent query budgets, mutable USPTO searches and publication/identity gaps
  remain; earlier 2015 releases do not satisfy the 2021 backfill requirement.
- Guidelines/payer policies, KOL disclosures, trial-site operating history,
  milestone coverage and additional conference abstracts still lack complete
  dedicated collection paths. Successful related sources do not close these gaps.
- Current snapshots and later revisions remain unsuitable for point-in-time
  inputs until field availability is verified. Source counts and pagination
  exhaustion certify the specified request only.

Do not check off end-to-end completion for a source with these unresolved
conditions. Existing scheduled collection continues under the memory and quota
limits. The register links exact query/date gaps and failure reasons.
