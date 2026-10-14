# Collection operations

The shared runners now call migrated collectors directly, using reviewed
universe 0.2.0. The daily origin is September 21, 2026. Configuration is in
`config/collection-operations.json`. This is an operational path for the
migrated source group, not completion of every source migration.

## Scope and identities

The default metadata scope retains unmatched discovery records. Document
downloads and derived event extraction use confirmed or candidate matches to
the shared universe. All four sectors and their overlapping memberships are
supported. Pending company identities remain candidates; normalized names
never establish confirmed legal identity. Both `cik` and legacy `sec_cik`
identifier namespaces are accepted, but only verified identifiers attached
to a unique verified legal company confirm an SEC match.

The current universe has 494 enabled company entities, 101 verified identities,
393 pending identities, and 34 ambiguous normalized name keys. Its 11 verified
CIK identifiers support 10 confirmed company matches; the remaining company's
identity is pending. These counts describe the current reviewed cohort, not
global sector coverage. EODHD and NMPA inventory jobs retain their independently
configured task identities.

## Commands

Use the project's Python 3.12 environment:

```bash
# No provider requests or cloud writes: inspect configured scope.
.venv-athena/bin/python -B collect_daily.py --dry-run

# Read source progress from S3 without fetching provider data.
.venv-athena/bin/python -B collect_daily.py --status

# Catch up completed calendar days from the fixed configured origin.
.venv-athena/bin/python -B collect_daily.py --max-windows 5

# Catch up, then revisit the previous three completed dates for revisions.
.venv-athena/bin/python -B collect_daily.py --max-windows 5 --reconcile-days 3

# Exact historical interval: start inclusive, end exclusive.
.venv-athena/bin/python -B collect_historical.py 2024-06-03 2024-06-04 --only sec --only fda
```

Historical START now defaults to **2015-01-01**, from
`config/historical-collection.json`. Use `collect_historical.py --end-date
2026-09-23 --dry-run` to inspect the full approved start through a pinned
exclusive end; explicit START END still selects a bounded cohort. See
HISTORICAL_COLLECTION.md for source limitations and all affected entry points.

Historical commands use YYYY-MM-DD dates. The old inclusive-month runner
interface is replaced; the requested interval is never expanded to month
boundaries. Monthly windows are clipped at both ends. Daily's optional date
sets the last included date; it still catches up from the configured origin.
A conservative cutoff requires both UTC and New York calendar days to be
complete. Source records retain their own date semantics and time zones.

Repeat the same command to continue partial windows. Limits bound each
invocation and do not change the task identity. Defaults permit 100 provider
pages, 10,000 SEC metadata records, and 5,000 derived input records per window.
The derived record limit counts examined inputs, including those outside the
selected company universe, not just downloaded documents.

Each source has independent date progress; a partial/failed window keeps that
source at the same date. Other sources continue. Each completed window must
have a committed, complete source manifest before the runner advances.
Daily and historical progress are separate, and a universe/configuration
change creates a new stream rather than silently reusing an old watermark.
Interrupted reconciliation dates remain in a persistent queue even if they
fall outside a later lookback. Updated parent manifests queue dependent work.

A local filesystem lock prevents simultaneous daily/historical runners on this
EC2 instance. Shared-store conditional writes also reject conflicting updates.
Do not independently run a direct collector on the same task while the runner
is processing it; use a different scope or wait for the scheduled run.

## Dependencies

`--only press-releases` automatically selects SEC, HKEX, document extraction,
and then press-release candidates. Licensing, M&A, and strategic-transaction
candidates use the same document prerequisite. Derived tasks receive explicit
completed manifests with matching universe, taxonomy, and calendar coverage.
Missing or partial prerequisites produce a blocked result. They never produce
a successful empty event dataset.

## Progress and provenance

Under the configured S3 research-data prefix:

- `operations/streams/<hash>/`: source date progress, latest window outcomes,
  and pending reconciliation dates.
- `operations/attempts/<uuid>.json`: immutable collector-attempt receipts.
- `operations/reports/<uuid>.json`: immutable multi-source execution reports.
- Existing `raw/`, `source_documents/`, `manifests/`, and `checkpoints/`:
  validated source evidence and collection records.

A caught-up source has completed its configured date interval. It does not
mean all available history has been collected. FDA zero-record results can be
complete when the provider query is exhausted. MHRA daily output is a current
snapshot; repeating a past date does not reconstruct the state on that date.
Current trial records selected by an update or registration date are likewise
not automatically historical versions.

## Scheduling and remaining work

The installed `optima-collection-daily.service` runs the shared daily path with
catch-up and a three-day reconciliation lookback. Its persistent timer is
enabled for 08:00 UTC plus up to 15 minutes of jitter. At installation its next
activation was September 23, 2026 at 08:03:29 UTC. It uses the same configured origin after restart.
EC2 downtime delays work; a missed timer activation runs after startup, and the
runner checks every unfinished date rather than skipping straight to yesterday.

EODHD profile collection and the NMPA ID inventory run through their existing
separate timers. ChiCTR can be selected explicitly with `--only chictr`, but
its recurring reconciliation schedule still needs dedicated validation.
NMPA detail collection, patents, news, market-price collectors, people, and
conferences still need integration. Unsupported source names cannot dispatch
legacy commands through the new runners.

Full historical backfills need source-specific start dates, source-limit
partitioning, and explicit coverage reports. The historical command is ready
for the migrated sources; no all-source, all-history completion is claimed.

Collection does not automatically replace Athena tables. The published pilots
retain their original universe snapshots until new immutable releases pass
curation and query validation. Ongoing publication and mixed-universe migration
remain separate work.

## Rollout validation on September 22, 2026

All 12 configured daily stages completed the September 21 source-calendar
window. Source counts included 1,901 SEC filings, 1,061 ClinicalTrials.gov
studies, 740 HKEX announcements, 45 CTIS records, 61 MHRA snapshot rows and
25 PMDA rows. FDA exhausted its query with zero records for that date.
Document and event counts are in reports/collection-daily-status-2026-09-22.json.
Caps were deliberately exercised for FDA, ClinicalTrials.gov and documents;
all then resumed to completion. The derived collectors remained blocked until
the document manifest completed.

A separate historical validation completed SEC and FDA for June 3, 2024
(exclusive end June 4). Its S3 operation report is
operations/reports/43984748-44f2-4637-b92f-3aac01bf94e5.json.
The final collection/storage/curation regression run passed 126 tests.
The research dependency file now includes pypdf's fonts extra, after real HKEX
PDFs exposed missing font support. Prior extracted observations remain immutable.

## Dated universe cutover configured September 23, 2026

`config/collection-operations.json` retains its 0.2 base universe and daily origin
2026-09-21. Its `daily_universe_epochs` entry switches collection dates from
2026-09-24 to universe 0.3.0. The timer is active/enabled and invokes this config.
The first normal run that can collect the completed September 24 window is on
September 25. Earlier date windows keep their old universe and stream/progress
keys; unfinished windows and pending reconciliation can still resume.

The runner splits daily work into epochs, each with a stable progress origin
and the existing per-source dependency rules. Closed epochs stop receiving fresh
lookback reconciliation after they age out, but pending dates remain eligible.
`--max-windows` applies per source per epoch. Status output retains the previous
shape for one epoch and returns `universe_epochs` when the date range spans both.

Historical mode ignores daily epochs and stays with the explicitly configured
base universe. For a deliberately new historical cohort with 0.3, pass
`--config config/collection-operations.v0.3.json`. Standalone collector defaults
and the NMPA baseline remain 0.2; where available, use a collector's `--universe`
option to choose 0.3 for new work. Changing a task's universe is not a way to
resume an existing task. No task checkpoints or previously completed source
manifests were rewritten during this cutover.

`reports/universe-cutover-2026-09-24.json` records simulated boundary checks,
stream IDs, verified universe release and timer state. It explicitly records
that live collection under the future epoch has not yet occurred. The S3 audit
is under `operations/universe_transitions/2026-09-24/`. See COMPANY_UNIVERSE.md
for the company/listing changes and reproducible Athena queries.
