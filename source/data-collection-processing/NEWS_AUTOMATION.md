# News automation

IBKR is excluded from the active source scope at the user's request.

`news_operations.py` runs hourly under `optima-news-collection.timer` and the
existing `.news-collection.lock`. It pins universe 0.3, the two existing provider
configs, daily origin September 23, 2026, and historical origin January 1, 2021.
Each provider has independent durable daily, reconciliation and history progress.
Only Marketaux has a configured observed archive; Finlight history before its
recent window remains unavailable. History stops at the daily origin to avoid
counting the same date in both lanes.

Each invocation attempts one day per lane/provider. Completed search scopes reuse
their checkpoints. Partial reconciliation resumes the same dated revision across
UTC days. The daily limit remains 40 reserved HTTP requests per provider, counting
retries. Per-invocation lane allowances are 24 daily, four reconciliation, eight
history. These are ceilings, not promised coverage or a backfill completion date.

Only windows with all configured sector/language searches complete enter the S3
`operations/news/publication-queue/`. Queue persistence precedes cursor advance.
The publication timer runs every ten minutes, processing two windows per invocation,
independently from collection. Failed windows retry after 30 minutes without
blocking all subsequent queue entries. Source data, Parquet and verification
receipts remain immutable; active partitions can move to reviewed newer releases.

New Athena tables in `optima_news_research`:

- `news_articles_windows`
- `news_observations_windows`
- `news_company_candidates_windows`
- `news_coverage_windows`

Each is partitioned by `window_id`. Reconciliation replaces the same logical
provider/date window after verification; it does not add duplicate active windows.
The four original pilot tables are retained as a snapshot. Do not union them into
the new tables: their September 23 records are already included. Observations are
versioned evidence; use the articles table for article counts. Provider queries do
not establish complete worldwide news coverage. Current text and company links
remain unsuitable for point-in-time model features without separate validation.

January 1, 2021 Marketaux: 44 observations, 41 distinct articles, four search scopes,
and 23 candidate company links passed live partition count verification.
September 23 Marketaux and Finlight windows are queued/published through the same path.

```sql
SELECT source, substr(published_at, 1, 10) AS publication_date, count(*)
FROM optima_news_research.news_articles_windows
GROUP BY 1, 2 ORDER BY 2, 1;
```

Validation covers partial resumes, stable reconciliation revisions, queue-write
failure, durable verification, and rollback of failed partition publication.
The systemd timers are persistent across restarts; local locks assume one EC2 host.
See `unused/reports/news-market-automation-verification-2026-09-24.json` for final live status.

September 26 recovery: changed-source or duplicate-page checkpoints trigger one
fresh attempt per search scope per UTC day. The restart receipt retains the old
manifest; completed sibling searches are reused. The same client request allowance
and durable daily quota apply to recovery, and incomplete windows stay unpublished.
