# Market coverage repair — October 21, 2026

The reviewed ticker repair is collecting and queryable in Athena. Six listing-specific exclusions are applied with saved primary evidence. The remaining market gaps are not all resolved.

| Measure | Before | After |
|---|---:|---:|
| Daily symbols with unresolved windows | 179 | 174 |
| Historical symbols with unresolved windows | 208 | 202 |
| Reviewed excluded windows, both lanes | 26 | 46 |

Counts describe unresolved windows, not a full trading-session completeness audit. Exclusions are tracked separately from collected records; none fabricate prices or remove raw evidence.

## Ticker change repaired

AADI.US became WHWK.US effective March 19, 2025, as confirmed by the [issuer's SEC-filed announcement](https://www.sec.gov/Archives/edgar/data/1422142/000119312525056708/d839636dex991.htm). Added an evidence-checked mapping registry to the market collector. Requests split at the effective date, including dividends and splits. An empty segment cannot make the whole window complete. Logical listing candidates remain unchanged; each record identifies its actual provider symbol and source URL.

Replayed 2025, January–August 2026, September 2026 and October 1–20, 2026. This also repairs a previously “complete” 2025 request that contained only old-ticker prices.

Verified **451 price rows** in four market Athena partitions: 51 AADI rows through March 18, 2025 and 400 WHWK rows from March 19, 2025. Per-window counts equal distinct dates; the boundary query returned zero incorrectly mapped rows. Inspected randomized payloads, including OHLCV, actual WHWK request URL and saved source evidence. Records remain candidate identity matches and are not represented as point-in-time eligible.

- Market count query: `42f4ad17-50fa-4094-80a3-6b5c4ae0b543`.
- Boundary query: `eaaed5ab-c5d3-49b0-b13c-b11ea33ae7e2`.
- Shared observations verification: `d4ac7359-4cb0-4521-8b3d-37efb4354bb4` (451 records).
- [Run the partition-bounded SQL checks](SQL-checks.md); [full query evidence](athena-verification.json).

The first typed publication attempt failed because native Parquet I/O bypassed the runtime filesystem adapter. Changed Parquet serialization to an in-memory buffer followed by the filesystem's byte-write interface. Retried the four exact partitions using a native temporary build directory; all four publication receipts now report verified. `publication-direct.log` contains the successful publication results. The earlier empty retry was skipped by the failure backoff; it was not treated as verification.

## Justified exclusions

Only windows wholly within these reviewed periods are excluded. Post-trading exclusions currently end January 1, 2027 and require review beyond that horizon.

| Listing | Excluded period | Evidence and distinction |
|---|---|---|
| AELIS.PA | January 2021–February 17, 2022 | [Euronext](https://www.euronext.com/en/about/media/euronext-press-releases/aelis-farma-lists-euronext-paris): first trading February 18, 2022. |
| 1SXP.XETRA | January 2021–September 27, 2023 | [Deutsche Börse](https://www.cashmarket.deutsche-boerse.com/cash-en/Data-Tech/statistics/New-Companies/SCHOTT-Pharma-AG-Co.-KGaA-3681168): SCHOTT Pharma first trading September 28, 2023. |
| ATLN.SW | 2021–2026 | [Depositary notice](https://depositaryreceipts.citi.com/adr/common/file.aspx?idf=4313): Actelion delisted November 7, 2017. |
| MMED.NEO | April 11, 2024–end 2026 | [Issuer SEC exhibit](https://www.sec.gov/Archives/edgar/data/1813814/000095017024039484/mnmd-ex99_1.htm): Canadian delisting after April 10 close. NASDAQ shares are not substituted. |
| 1CO.XETRA | 2026 only | [Exchange notice](https://www.cashmarket.deutsche-boerse.com/cash-en/Stay-Informed/newsroom/Xetra-Frankfurt-Newsboard/XETR-Deletion-of-Instruments-from-XETRA-05.12.2025-4841756): tendered Covestro shares, ISIN DE000A40KY26, last traded December 5, 2025. |
| 1COV.XETRA | 2026 only | [Issuer annual report](https://annualreport.covestro.com/annual-financial-report-2025/en/report/capital-market/covestro-shares/): ordinary-share Xetra trading ended December 22, 2025; Frankfurt continued. Provider has a December 23 observation, preserved as a discrepancy. Conservative exclusion starts January 2026. |

1CO and 1COV are distinct securities, not interchangeable aliases. Earlier 1CO gaps remain unverified. Each decision retains listing IDs, exact date boundaries, reviewer, explanation and checksum-verified source documents. See `decisions.json`, `covestro-decisions.json`, `primary-evidence.json` and `final-coverage.json`. Existing exclusion tooling supports revocation.

## What remains

[Coverage review CSV](coverage-review.csv) inventories the original 1,123 flagged windows across 230 symbols and marks the repairs/exclusions above. Initially 557 windows followed the provider's last price, 238 preceded its first price and 328 belonged to symbols with no returned price history. Those provider dates alone do not prove IPOs, delistings or suspensions. No original flagged window fell inside the provider's returned min/max range, but that does not establish completeness of individual trading sessions.

Remaining cases need exchange/issuer evidence or provider correction. For example, AESGENER.SN / AESANDES.SN remains unresolved: the proposed target returned no prices, so no speculative mapping was applied. No new API key is required for the verified repair.

For each remaining case:

1. Confirm legal issuer, security class, venue, currency and effective dates from issuer/exchange evidence.
2. If the same security changed ticker, probe the target, register a reviewed date-bounded mapping, then replay both sides of the boundary and query Athena.
3. If trading was impossible, save the evidence and add an exact listing/date exclusion. Never infer this solely from an empty response.
4. If trading occurred but prices are absent, request a provider correction or assess a separately identified alternative source. Keep the gap open until records are verified in Athena.
5. Separately audit expected trading sessions within nonempty windows; successful requests and min/max dates are insufficient for that check.

## Your next check

1. Open `SQL-checks.md` beside this report.
2. Run the count and boundary queries, then the 20-row sample in Athena.
3. Inspect OHLCV and `record_json.payload.provider_symbol`. `symbol = AADI.US` is the retained logical listing; post-change requests correctly use WHWK.US.
4. Flag any field/identity mismatch you find. Remaining evidence gathering and mapping repairs are engineering work; you do not need to buy another subscription for this repair.

Validation: 39 market collection/operations/exclusion/mapping tests passed, plus live source replay and Athena verification. All 66 previously active timers, including the backup timer, were restored with no state mismatches. Reddit, Bluesky and GitHub timers retain their prior paused states. See `schedule-restoration.json`.
