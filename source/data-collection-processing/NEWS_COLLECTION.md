Recurring collection, reconciliation, Marketaux 2021 backfill, and verified Athena window publication are now scheduled. See NEWS_AUTOMATION.md for current status; earlier rollout notes below are historical.

# Shared news collection

`news_collection.py` migrates Finlight and Marketaux to the shared S3 research
layout. `ticker_news.py daily ...` and `ticker_news.py historical ...` dispatch
to this collector; the old positional ticker-triplet interface remains a legacy
path and still uses its original company-specific output bucket.

Configuration is `config/news-collection.json`: universe **0.3.0**, all four
sectors, source evidence and JSONL in bucket
`data-collection-059416028963-us-east-1-an`, prefix `research-data/`.
Keys are read from Secrets Manager `newKeys` on EC2. Credential values and
authenticated request URLs are excluded from stored evidence and failure logs.

Each task is one provider, query, language and date window. Historical windows
are monthly; daily windows are UTC days. The default historical origin is the
shared **2021-01-01** policy. Dates use inclusive starts and exclusive ends.
Requests overlap date boundaries by one second; out-of-window boundary articles
are retained only in raw provider evidence, not normalized records. A provider
ignoring the requested dates causes failure rather than silent ingestion.

Sector queries include biotech, robotics, semiconductors, batteries,
supercapacitors, thermal, mechanical and hydrogen storage. English and Chinese
terms provide discovery; they do not exhaust global terminology. Finlight has
separate `en` and `zh` tasks. Marketaux omits its language filter to accept its
supported languages, including those returned by the live pilot.

`--company-id` builds a query from that enabled shared-universe company's name
and non-rejected aliases. This avoids treating an unqualified ticker as a global
identity. Aliases and provider company names create **candidate** links, not
verified identities. Search hits outside the current universe are retained for
review and private-company discovery. Dates on historical aliases and listings
still need review before treating them as historical identity evidence.

## Plans and historical gaps

The user confirmed **Marketaux Standard** and **Finlight Pro Light** on
September 24, 2026. Source documentation checked that day:

- [Marketaux pricing](https://www.marketaux.com/pricing): Standard allows 50
  articles per request and 10,000 daily requests. The live API returned a
  50-article page limit. The collector reads actual pagination metadata and
  requests 50 under the confirmed configuration.
- [Finlight limits](https://docs.finlight.me/en/v2/rate-limits/) describe Pro Light
  as approximately the last month of history, with older dates returning no
  results. [Pricing](https://finlight.me/pricing) excludes historical data from
  Pro Light. We use a conservative **28-day** recent window and explicitly defer
  older periods as `provider_history_unavailable`. This is a conservative
  collection boundary, not a claim that the provider guarantees precisely 28 days.
- [Finlight multilingual documentation](https://docs.finlight.me/en/v2/advanced-query-building/)
  requires a separate request per language. There is no all-language wildcard.
- [Marketaux documentation](https://www.marketaux.com/documentation) describes
  date filtering and a 20,000-result pagination ceiling, but the reviewed public
  documentation does not establish its earliest news archive date.

The January 2015 live probe returned **zero articles** for all four English
sector queries from both providers. This does not prove that those periods had
no relevant news. Finlight's plan cannot establish 2015 coverage; Marketaux's
2015 archive coverage remains unverified. Broad historical publication is
therefore blocked by explicit coverage gaps. A documented `history_start` and
`history_evidence` are required before Marketaux historical tasks can complete.
An alternative archive may be necessary where verified 2021-onward coverage is unavailable.

Finlight's empty response used `pageSize=0`; its nonempty responses used the
returned count, not always the requested limit. The implementation accepts this
observed shape and requires an empty terminal page. It never mistakes a short
page for guaranteed completion. Marketaux completion uses `found`, `returned`,
`limit` and `page`; truncation, total drift and result ceilings remain explicit.

## Resumption and bounded operation

Each committed page has raw response/request evidence, normalized JSONL batches,
an immutable run manifest and a checkpoint. Resumption checks the last committed
provider page before continuing offset pagination. Changed pages/counts and
duplicate article IDs stop for a controlled `--refresh`. These checks detect
common shifts but cannot turn mutable provider searches into frozen snapshots;
late-indexed articles and older corrections need later reconciliation.

Both providers currently have a conservative **40-request UTC-day cap for this
collector**, with request reservations in S3. Per-invocation request and task
caps apply as well. Retries and ambiguous network outcomes consume reservations.
This does not measure usage by other applications sharing the credentials.
Quota/entitlement errors are partial runs. A local `.news-collection.lock`
prevents overlapping workers on this EC2 host; it is not a distributed lock.

```bash
# Inspect the approved historical origin without network calls.
.venv-athena/bin/python -B ticker_news.py historical --end 2021-02-01 --dry-run

# Yesterday by default; explicit bounds make retries reproducible.
.venv-athena/bin/python -B ticker_news.py daily \
  --start 2026-09-23 --end 2026-09-24 \
  --max-pages 6 --max-tasks 12 --max-requests 20 \
  --output unused/reports/news-daily-complete-2026-09-24.json

# Historical request: records an explicit gap until archive access is established.
.venv-athena/bin/python -B ticker_news.py historical --provider marketaux \
  --end 2021-02-01 --max-requests 4

# Read back saved evidence; this makes no provider API calls.
.venv-athena/bin/python -B news_audit.py \
  --report unused/reports/news-daily-complete-2026-09-24.json \
  --output unused/reports/news-daily-complete-audit-2026-09-24.json
```

Completed tasks are skipped on rerun. Limits leave explicit partial/unattempted
counts rather than claiming full collection. `--probe-history` allows bounded
unverified archive sampling; it does not authorize marking coverage complete or
bypass Finlight's known plan restriction. `--refresh` starts a new retained
attempt for the exact selected scope. Previously committed attempts remain.

## Athena example

The complete September 23 daily cohort contains **1,042 observations** across
12 queries. Curation produces **964 distinct provider article records**:
483 Finlight and 481 Marketaux. Repeated hits within a provider are deduplicated;
articles syndicated across providers are not silently merged.

Database: `optima_news_research`, workgroup: `optima-news-research`, region:
`us-east-1`. The pilot uses the shared 100 MiB per-query safety limit.

**Live and verified September 24, 2026:** all three Athena checks passed
(quality safeguards, provider counts, and four table counts). The S3 read-back
audit verified all 1,042 observations and 51 source/request evidence objects,
including empty terminal-page responses. There are 81 candidate company links.

Release ID:
`8afd2952a4460f3157c6c6cdb9c65a9dd2257de282fcba152ed58f0c48eab131`.
Release prefix:
`s3://data-collection-059416028963-us-east-1-an/research-data/curated/news/releases/8afd2952a4460f3157c6c6cdb9c65a9dd2257de282fcba152ed58f0c48eab131/`.
Local verification is under the matching `news-athena-build/` directory.

| Table | Purpose |
|---|---|
| `news_articles` | Latest observed article, source, language, publication timestamp, candidate sectors and revision/observation counts. |
| `news_observations` | All source observations and raw record JSON, with manifest and evidence links. |
| `news_company_candidates` | Candidate company links, explicitly pending review. |
| `news_coverage` | Exact completed query/language windows and observation counts. |

Repeated discovery queries do not invent article revisions: revision hashes use
the provider article payload. Corrected provider payloads remain separate
versions in observations. All articles have `available_at=NULL` and
`point_in_time_eligible=false`; a current copy of an old article, its entities or
sentiment is not automatically safe as a historical training feature.

```sql
SELECT source, query_target, language, window_start,
       window_end_exclusive, observations
FROM optima_news_research.news_coverage
ORDER BY source, query_target, language;

SELECT source, language, published_at, title, candidate_sector_ids
FROM optima_news_research.news_articles
ORDER BY published_at DESC
LIMIT 25;
```

Release tools:

```bash
.venv-athena/bin/python -B news_athena.py prepare --collection-report REPORT_JSON
.venv-athena/bin/python -B news_athena.py publish --release-dir RELEASE_DIRECTORY
.venv-athena/bin/python -B news_athena.py deploy --release-dir RELEASE_DIRECTORY
```

Only a complete cohort can be prepared. Curation verifies committed manifests,
raw hashes/counts, record schemas, universe hashes and source evidence. Parquet
round-trips locally and is read back after upload. Deployment verifies table and
provider counts and checks that no article is marked model-ready. This is a
bounded pilot, not recurring incremental news publication. Existing conflicting
table releases are rejected by this CLI. Multi-table deployment is not atomic;
check the release's final `athena-verification.json` for successful verification.

Validation: **81 relevant tests passed**, including pagination changes, explicit
history gaps, caps, retries, credential protection, raw corruption, article
deduplication and preservation of real revisions.

Current remaining work: verify broad Marketaux archive coverage, expand
language/terminology and company queries, and review candidate identities.
Daily catch-up, reconciliation and incremental publication are now scheduled;
see NEWS_AUTOMATION.md. IBKR is excluded from scope. Prices and splits/dividends
now have their own migrated pipeline; see MARKET_COLLECTION.md.

## September 24 archive follow-up

Unfiltered Marketaux samples returned articles in each sampled year 2021–2026;
2015–2020 queries returned zero, which does not establish absence of news.
The January 1, 2021 four-sector cohort completed with 44 observations
(8 biotech, 16 energy storage, 6 robotics, 14 semiconductors), not yet published
in Athena. See `unused/reports/marketaux-history-years-2026-09-24.json` and
`unused/reports/marketaux-historical-four-sectors-2021-01-01.json`.
`config/news-history-marketaux.json` records the observed 2021 floor;
the shared historical target is now 2021; these samples do not establish full archive coverage.
