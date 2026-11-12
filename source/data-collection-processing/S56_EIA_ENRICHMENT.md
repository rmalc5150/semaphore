# S56 EIA archive and retail enrichment

Only `eia_generator_index` and `eia_retail_prices` are changed. The existing
`eia_battery_generators` adapter, configured archives and observations are unchanged.
All outputs remain in dataset `specialist_inputs`, using the existing committed
S3/Athena publisher and original source record identities.

## Generator archive catalog

Actual HTML anchors are parsed rather than searching raw HTML for every href.
The saved index had 139 regex-discovered links per capture but only 135 actual
workbook/code-reference anchors; four commented template months are not evidence
of publication. The backfill checks each saved link against its hash-verified
original HTML and classifies non-anchor templates explicitly. Future-period links
are not downloaded or treated as releases. The parser prioritizes recent months
and pins its discovered link list/evidence in a durable page cursor.

For each actual archive, validate the official HTTPS URL, XLSX signature and ZIP
expansion limits, archive original bytes, and parse sheets using streaming reads.
Enrichment retains the source month/filename basis, SHA256, introductory cells,
sheet headers, row counts, distinct Plant ID + Generator ID counts, state/status/
prime-mover distributions and separate reported capacity sums for MW-labelled
fields. MWh is never added to MW. No generator unit rows are published by this
index enrichment. Code-reference workbooks are identified separately. A provenance
pointer specifies how to join to the existing battery table; it does not certify
that table's completeness or create unit/company/product associations.

Cache recent four-month workbooks for up to 24 hours and older files/code references
for up to 30 days. Cache evidence keeps its actual original retrieval timestamp.
Metadata and hash receipts are saved under `operations/eia-enrichment/archive-heads/`
and `archive-versions/`, with raw originals under source documents. Changed hashes
nominate revision review, not proof of physical capacity changes. A workbook month
is not a publication or commissioning date. Invalid responses remain explicit gaps
and are reconsidered on future daily discovery; they cannot become valid workbooks.

The normal daily adapter processes five links per page with checkpoints, so a
bounded invocation can be partial and continue under the existing daily timer.
Live normal-adapter verification committed five validated workbook summaries for April–August 2026. August retains a duplicate-identity review flag; it is not silently certified as clean.
Source-specific task versioning prevents old metadata-only completion receipts
from suppressing the enriched collector.

Live validation of January 2018 found 27,797 distinct generators across Operating,
Planned, Retired and Canceled or Postponed worksheets. See
`reports/eia-generator-index-live-verification-2026-10-18.json`; normal daily-page
capture is recorded in `reports/eia-generator-index-daily-live-2026-10-18.json`.

## Retail electricity context

The existing scope stays US total, all customer sectors, monthly. EIA API metadata
provides definitions/units and the available data period. The collector requests
price, sales, revenue and customers together, adding a twelve-month lookback for
MoM and YoY baselines. All pages are exhausted with total/scope/duplicate checks;
only target-window rows are published. Requests and API echoes never expose the
credential in saved evidence or errors.

Preserve provider strings, missing/non-numeric markers and units; normalize finite
values to decimal strings. Supported price conversion is cents/kWh divided by 100
for USD/kWh. Comparative changes require matching units and nonmissing baselines.
A revenue/sales price reconciliation is calculated only for compatible provider
units. Changes are not seasonally adjusted and do not establish a specific tariff,
wholesale price, storage arbitrage opportunity or company financial effect.

Daily current-observation heads detect revised same-period metrics, ignore pure
numeric-format changes, and preserve the previous observation time. Raw provider
responses and immutable operational revision observations remain available. No
original public-release date or historical model eligibility is inferred.

During setup the metadata route worked and reported an end period of July 2026,
but the data route timed out / returned HTTP 504 for bounded historical and current
queries. Tests cover the collector and comparison logic, but live multi-metric
retail output remains unverified until the upstream data route recovers. See `reports/eia-retail-live-verification-2026-10-18.json`. The daily
scheduler retries these transient failures after 30 minutes. Backfill defers without
consuming per-record attempts; an ongoing API outage cannot produce a false
successful completion email.

## Correct backfill and notification

`config/eia-enrichment-backfill.json` pins 85 committed input batches: 1,390 index
observations and 75 retail observations. Index captures are grouped by archive URL;
retail captures group only unchanged source-row content, preserving revised values.
The 67 distinct saved months cover January 2021 through July 2026 with no missing
months. This audited coverage and its hash are pinned in
`reports/eia-enrichment-backfill-2026-10-18/retail-coverage.json` and rechecked at run
time. All originally discovered archive periods are retained, including older
context and explicit unpublished-template classifications.

The backfill preserves each original record identity, event date and saved data.
Index metadata describes an archive retrieved now, not a reconstructed old workbook
vintage. Retail original prices stay intact; current-retrieved metrics/baselines,
changes to original fields and their separate evidence appear under enrichment.
No historical publication availability is invented.

`eia_enrichment_backfill.py` and `optima-eia-enrichment-backfill.timer` resume bounded
work every five minutes. Permanent record errors retry up to three times; transient
retail API errors are deferred for 30 minutes without exhausting attempts. Local
progress is `reports/eia-enrichment-backfill-2026-10-18-latest.json` plus the matching
SQLite registry; durable state and receipts are under
`operations/eia-enrichment/enrichment-backfill/eia-enrichment-backfill-2026-10-18/`.

Completion email uses the existing confirmed subscription for
randall@optima-holdings.com and waits for every pinned source version to have an
output plus exact per-source job counts verified in Athena. Counts distinguish
unpublished templates, enriched, review-required and gap outcomes; the gap receipt
and limitations accompany completion with gaps. No completion is claimed while
retail provider deferrals leave versions pending.

Use `payload.data.enrichment`. Source observations and pending event candidates do
not enable the main event ledger, RDS matching or specialist models. Integration
requirements are recorded in the S56 section of `ENTITY_DISCOVERY_ROLLOUT_PLAN.md#event-pipeline`.

Validation:
`python -m unittest test_eia_enrichment test_eia_enrichment_backfill test_specialist_inputs test_specialist_authenticated -q`.
