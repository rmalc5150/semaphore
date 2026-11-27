# Oversized inputs and lower-severity alerts — 13 November 2026

The ordinary capture workers continue. Oversized metadata evidence now uses a separate disk-backed validation lane on the m7 worker. The owner-paused Reddit, Bluesky, GitHub, Marketaux and NICE routes remain paused.

## Repairs completed

- Stream original S3 objects to temporary files in 1 MiB chunks; verify SHA-256 and complete object length. Validate PDFs, SEC complete-submission SGML, ZIP exports, CSV files and the large consolidated trade-screening JSON response without loading the entire artifact into a Python bytes object.
- Check ZIP member CRCs and lengths, archive size/expansion limits and unsafe paths. Recognize CORDIS semicolon CSV exports and HKEX native fixed-width `.lis` reports. SEC submissions require matching accession/CIK URLs and closed substantive document blocks. Screening rows must exactly match the archived original; both the legacy provider ID and the collector's documented list-plus-ID identity are checked.
- Route oversized inputs out of ordinary metadata workers into `optima-metadata-streaming.timer`. One process, four jobs per run, 768 MiB memory cap, 75% CPU cap, 15-minute service timeout, 512 MiB maximum original and 4 GiB maximum archive expansion. Source rotation and an independent lock prevent a large source from monopolizing other queues. Temporary files are removed after each invocation. Insufficient pool RAM defers this lane.
- Added bounded publication of exact repaired job IDs. It uses the existing Glue/Athena count verification and durable receipt, without moving the normal publication cursor past other sources.
- Removed the duplicate **daily** `optima-patents-reviewed-odp.timer`. The canonical m7 daily collector committed progress without the previous conflicting S3 checkpoint write. Historical and assignment schedules remain enabled. Local partial `request_limit` now means continuation; failed requests, HTTP 429, integrity failures and stalled progress retain their alerts.
- Published and queried the November 6 recovered Finlight window: **1,111 distinct article rows and 1,245 observations**. All 1,111 have titles and provider payloads. Latest capture in this window: November 13, 09:05 UTC. Representative payloads contain summaries and some have `full_text_status=pending`; this verifies news capture/publication, not complete article-text enrichment or historical completion.
- Mapped `AAPGV.US` to `AAPG.US` from January 27, 2025, retaining the original listing candidate and actual provider symbol in every row. The issuer confirms the January 24 when-issued listing and January 27 regular-way transition; a budgeted provider probe returned current AAPG prices. Excluded only the evidenced US pre-IPO interval before January 24. Four historical/daily windows now contain **218 verified Athena price rows**, January 2–November 12, 2026. Each has a close and the `AAPG.US` provider mapping. Existing mappings/exclusions were retained.

Primary issuer evidence: [Ascentage listing announcement](https://www.ascentage.com/ascentage-pharma-was-successfully-listed-on-nasdaq-becoming-the-first-dual-listed-18a-company-on-the-u-s-stock-market/). Original HTML and provider responses are archived with checksums under `source_documents/market_coverage_review/`.

The temporary controller memory increase used for publication was restored: `optima-financial.slice` MemoryHigh 320 MiB / MemoryMax 384 MiB. Both repair runtime checkpoints passed. No instance upgrade or new API credential was required for these repairs.

## Athena evidence

`exact-publication.json` records actual Athena query IDs and results for the originally oversized inputs. These are specific repaired jobs, not the entire source history. Raw originals remain linked by S3 URI and checksum. ZIP/PDF validation publishes the file/document observation and provenance; it does not normalize every spreadsheet cell or extract every PDF paragraph into specialist features.

| Source | Audited Athena observations | With a streamed original |
| --- | ---: | ---: |
| `indonesia_esdm_and_geological_agency_mineral_statistics` | 1 | 1 |
| `trade_screening` | 288 | 288 |
| `european_commission_cordis` | 2 | 2 |
| `bis_sdmx_api` | 4 | 4 |
| `hkex_prices` | 3 | 3 |
| `faostat_food_balances` | 3 | 3 |
| `personnel_archive` | 1 | 1 |
| `university_technology_transfer_catalogs_and_reports` | 1 | 1 |
| `hkex_news` | 28 | 1 |

Other durable evidence:

- `news-articles.json`, `news-observations.json`, `news-payload-sample.json`, `news-receipt.json`.
- `market-athena-readback.json`, `aapg-publication.json`, `market-state-after.json`.
- `news-publication.json` and `market-aapg.json`: exit status, durable logs and verified S3 checkpoints. Earlier failed repair attempts are retained in the append-only logs; the final attempts succeeded.
- `composite-trade-publication.json`: another **32 fresh screening rows**, all raw-complete and carrying the documented composite identity, verified after the identity correction. This batch is separate from the 288-row screening snapshot in the table.
- `final-worker-health-result.json`: all nine affected sources enabled; ordinary and streaming metadata timers enabled/active. One unrelated HKEX original HTTP 404 remains recorded.
- `metadata-deployment-result.json` and deployment manifest: exact code hashes and worker deployment results.
- `monitor-health-after.json`: current source issues; an empty issues list does not certify historical completeness.

## Remaining work, in priority order

1. **Market evidence review:** **174 daily and 201 historical symbols** still have unresolved windows. `remaining-market-windows.csv` lists **1,091** explicit saved gap windows, with the remaining US symbols first. Some current-month incomplete attempts are represented by the source's latest result rather than a stored gap entry. Classify ticker transitions, provider coverage failures and impossible periods individually. Empty API responses alone cannot establish that no trading occurred. The remaining US symbols in this saved gap inventory are `AAAP_old.US` and `ABHBY.US`. Do not suppress these without issuer/exchange evidence.
2. **Patent mutable-source recovery:** the canonical daily source can still change while paginating. Its existing refresh/cooldown recovery remains separate from a normal page/request allowance. Verify the affected window's next recovery checkpoint; the service remains scheduled. Retain the alert until recovery has committed evidence.
3. **Continue the bounded streaming/publication backlog.** A successful representative replay does not mean every waiting batch is already published. The permanent timer and ordinary publisher continue independently. New unsupported formats or genuine identity mismatches remain explicit failures.
4. **Separate content gaps:** the repaired personnel batch includes one verified large SEC original, while four other parent-content gaps remain recorded and excluded from raw-complete output. News full-text enrichment remains separate where the provider payload says pending. An unrelated HKEX original also returned HTTP 404; that gap remains recorded while its source continues. These gaps are not silently promoted to complete.

## What you need to do

No new account, key, purchase or manual restart is needed **for the repairs above**. To inspect them yourself:

1. In Athena, use the query SQL and IDs in `market-athena-readback.json` and `news-articles.json` / `news-payload-sample.json`.
2. Inspect the 218 mapped market prices and sample the news payload fields. Note the full-text status rather than assuming a summary is a complete article.
3. For remaining market exclusions, supply issuer/exchange evidence if you already have it; otherwise they remain an engineering/source-coverage review task. Keep the saved gap list until each exact listing/date interval is resolved.

## Validation

79 focused regression tests passed across streaming, metadata evidence/runtime/publication, grants/procurement and alert behavior. Live checks include original checksums, format integrity, committed raw manifests, actual Glue/Athena publication receipts and representative Athena payloads. The new lane is isolated by its own memory/CPU limits; no global raw-byte limit was raised for ordinary workers.
