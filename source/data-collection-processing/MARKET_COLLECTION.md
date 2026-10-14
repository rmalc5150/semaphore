# Market prices and corporate actions

Shared collection is implemented in `market_collection.py`. The primary scheduled
feed is EODHD, using the upgraded existing account. `market_operations.py` pins
universe 0.3's 492 non-rejected provider listing symbols. Links remain candidate
listing identities; no name-based company merge is performed. The official HKEX
quotation collector also has a shared evidence/checkpoint path for bounded dates.
The old Yahoo cross-listing CSV enrichment is not the scheduled global feed.

Historical collection starts January 1, 2021, in windows of at most one year,
ending at September 1, 2026. Daily collection refreshes the current calendar month
through yesterday; it catches up missed months before advancing. Historical and
daily progress are independent per symbol. Daily tasks have priority over the
historical queue; a failed symbol is deferred until the next UTC day while other
symbols continue. Empty price responses remain explicit unverified gaps, with no
completed cursor or Athena publication. A configured universe is not global coverage.

The collection timer runs every 15 minutes. Runtime limits from
`config/eodhd-quota.json` override the original deployment bounds: 80 symbol
windows per lane, 300 requests per invocation, and 9,000 market calls per UTC day.
All configured EODHD clients share a durable weighted 98,000-call daily ceiling
and rolling 900-request/minute guard, preserving 2,000 units below the plan limit.
Reservations precede every HTTP attempt, including retries. Profile, market and
inventory allocations share that guard; account changes/unverified quota fail explicitly.
See EODHD_QUOTA.md. The original market stream identity is retained.

Records retain raw source evidence, current observation times, unadjusted and
provider-adjusted prices, split ratios, and dividend source fields (including
unadjustedValue and declared/record/payment dates where supplied). Historical
adjusted prices and volumes may incorporate later actions. Dividend `value` can
be adjusted; `unadjustedValue` is preserved in data_json. Neither is silently
relabeled as point-in-time data. Currency is retained where provided; EODHD price
responses that omit currency keep it null rather than infer it from a company.
Coverage is splits and dividends; other corporate actions remain a coverage gap.
Old-year adjusted-price revisions require a separate reconciliation policy.

Official HKEX: Main Board and GEM progress resumes independently; the requested
date must be present in the sheet. Missing pages do not establish exchange holidays.
All quoted instruments are retained for discovery, including instruments outside
the company universe. These sheets do not supply opening/adjusted prices or actions.
The daily scheduler uses EODHD for mapped Hong Kong and foreign listings. The
HKEX adapter can be invoked manually for a bounded official-source comparison;
full official-HKEX archive coverage is not established.

Completed windows enter `operations/market/publication-queue/`. The publication
timer processes up to 24 windows every ten minutes. Three partitioned tables in
`optima_market_research` contain current verified releases:

- `market_prices_windows`
- `corporate_actions_windows`
- `market_coverage_windows`

Daily refresh replaces the same symbol/month partition. Prior releases and raw
observations remain in S3. Publication verifies Parquet round trips and raw/evidence
hashes, then Athena row counts; on failure it restores the previous partitions.
Each successful window has a durable S3 verification receipt. Original provider
rows and timestamps remain in record_json, and listing candidates are explicit.
Prices from different providers must not be summed as if they were independent
trading sessions.

Live pilots: official HKEX September 23 returned 17,644 quotation records; EODHD
NVIDIA 2021 returned 252 price rows, four dividends and one split. Subsequent
multi-exchange windows are being collected and published incrementally.

```bash
.venv-athena/bin/python -B market_operations.py --status
.venv-athena/bin/python -B market_collection.py eodhd historical \
  --symbol NVDA.US --end 2022-01-01
.venv-athena/bin/python -B market_collection.py hkex daily \
  --start 2026-09-23 --end 2026-09-24
```

```sql
SELECT source, symbol, count(*) FROM optima_market_research.market_prices_windows
GROUP BY 1, 2 ORDER BY 1, 2;
SELECT symbol, event_date, kind, amount, share_multiplier, data_json
FROM optima_market_research.corporate_actions_windows WHERE symbol='NVDA.US';
```

Provider references checked September 24, 2026:
[EOD historical data](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes)
and [splits/dividends](https://eodhd.com/financial-apis/api-splits-dividends).
The APIs use inclusive `to`; the shared collector converts its exclusive end to
the preceding day and validates every returned date.

## September 26 gap recovery

Empty price windows remain partial and retain a provider-history availability
probe with first/last observed quote dates. These are provider coverage boundaries,
not verified listing dates. Historical automation uses a separate `scan_next_date`
to try later years, retaining empty windows in `gaps`; `next_date` does not advance
past unresolved gaps. Once the scan reaches the daily origin, gap retries continue.
Daily unavailable windows retry on following days. Status reports count unresolved
symbol windows even when a particular invocation has no work to do. Existing
weighted provider quotas and per-run request limits also cover diagnostic probes.

## September 27 gap retry repair

After scanning all historical windows, retries select the least recently attempted
gap, with date as a tie breaker. Previously, the earliest unresolved year was
selected indefinitely, starving later gaps. Each gap retains its own attempt time;
a gap is removed only after its collection completes. Empty-price and unresolved
coverage alerts remain active until source evidence resolves them.

Reviewed, evidence-backed exclusions can now distinguish impossible/unavailable
windows from actionable gaps. They stop retries without claiming collection or
publishing fabricated empty datasets. See [MARKET_COVERAGE_EXCLUSIONS.md](MARKET_COVERAGE_EXCLUSIONS.md)
for scope, evidence, reporting and reversible review commands.
