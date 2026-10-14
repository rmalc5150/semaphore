# Patent scheduling

`patent_operations.py` manages USPTO daily updates and explicit historical ranges
using company universe 0.3.0. Existing patent manifests and other collectors'
progress are preserved. All returned USPTO records are retained as evidence;
company-name candidates and technology rules cover all four agreed sectors.
These candidates still require evidence-based review before curated publication.

Daily catch-up starts with provider ingestion day **2026-09-22**. The provider's
timestamp timezone is unknown; these are provider calendar days. Historical
collection uses filing dates, with an exclusive end and monthly windows. Daily
updates therefore include newly ingested records for older filings.

The timer runs hourly at minute 30 UTC, with up to five minutes of random delay.
Each invocation attempts one window and at most 2,000 pages of 50 records,
including empty hourly queries. The September 27 repair partitions daily scans
into 24 disjoint, half-open provider-hour ranges. Each hour checks its own total,
sort order, timestamps and page sizes. Completed hours are committed to the parent
day with the child manifest and original source evidence retained. A changing hour
stops the attempt; the next invocation bisects its query range and preserves
completed subranges. Repeated drift can split ranges down to at most five minutes,
then only that small range is restarted. Completed hours are preserved. The daily date marker advances only after all 24 hours complete.

Page-limit and interrupted runs resume the active hour. An explicit daily refresh
creates a new child generation, so it cannot reuse stale completed hours. Existing
completed days, the stream identity, historical collection and old whole-day
manifests remain intact. Runtime and API request limits remain unchanged: one
request per second, a two-hour deadline, and the existing memory cap. The 50-record
page size avoids the previously observed HTTP 413 with 100-record requests.

Legacy whole-day scans retain the six-hour source-change restart cooldown. The
scheduled daily path selects `daily_partition_strategy: hourly-v1` in configuration.
A consistent count does not prove snapshot isolation. After catch-up,
the most recent two completed days are refreshed at most once each UTC day;
unfinished reconciliation remains pending beyond that lookback. Throughput and
source mutation may delay catch-up: the configured limit is not a guarantee of
complete daily coverage. EC2 must run for these jobs to execute. Persistent timers
trigger after boot; S3 progress determines the backlog rather than timer history.

```bash
# Read completed-date progress and the latest manifest count.
.venv-athena/bin/python -B patent_operations.py daily --status

# Review planned work without contacting providers or S3.
.venv-athena/bin/python -B patent_operations.py daily --dry-run

# Resume a bounded manual slice, sharing the scheduled checkpoint.
.venv-athena/bin/python -B patent_operations.py daily --max-pages 2

# Historical default is 2015-01-01; keep the exclusive end pinned.
.venv-athena/bin/python -B patent_operations.py historical \
  --end 2026-09-23 --dry-run

systemctl list-timers 'optima-patents-*'
journalctl -u optima-patents-daily.service -n 30 --no-pager
```

The process exits 0 when the requested work is caught up, 2 when bounded work or
reconciliation remains, and 1 for a failed collection attempt. The service accepts
exit 2 so normal pagination can continue at the next timer tick; inspect S3 status
and journal output for data completion, rather than relying on service success.
The collection monitor reports source failures separately from process status.

HTTP 413 recovery reduces the requested page size at the same offset until the
source accepts it, with a minimum of one record. Every attempt consumes the page
budget. Successful checkpoints retain the effective page size across resumes;
task identities and already committed records remain unchanged. A 413 for one
record stays an explicit failure. Source total and ordering checks still apply,
so a changed result set follows the existing partition refresh procedure.

S3 keys below `research-data/`:

- `operations/patents/streams/<stream>/`: window outcomes, progress and reconciliation.
- `operations/patents/reports/`: immutable invocation reports.
- `operations/patents/global-source/observations/`: immutable source metadata observations.
- `operations/patents/global-source/latest-observation.json`: latest observed revision.
- Shared raw batches, evidence and collection manifests retain the normal layout.

The global monitor checks BigQuery metadata daily at 07:15 UTC, plus jitter. It
uses federated credentials and metadata GET requests only; it submits no query
jobs. Observing a revision never marks its data collected. On September 23 at
18:33 UTC, the source reported 173,516,400 rows and a modification time of 17:59:58
UTC that day, versus 170,418,479 rows and an April 26 modification time in the prior
verification. Country publication-date coverage must be measured again.

Global paid backfill queries are now scheduled separately by
`optima-patents-backfill.timer`, starting 2015-01-01. The bounded runner checks
each new query's cost and records daily reservations. See
[PATENT_BACKFILL_OPERATIONS.md](PATENT_BACKFILL_OPERATIONS.md).
Temporary BigQuery results can expire, so a multi-day pause must not silently
launch a replacement billed query. Existing fixed-job checkpoints are preserved.

New raw collection does **not** update the reviewed Athena patent snapshot.
The existing January 2025 pilot remains queryable. Incremental curation,
review/publication checks are next. The updated global freshness and cost check
is now complete: see [PATENT_BACKFILL_PLAN.md](PATENT_BACKFILL_PLAN.md) for the
September 23 evidence and unexecuted historical-range proposals.
