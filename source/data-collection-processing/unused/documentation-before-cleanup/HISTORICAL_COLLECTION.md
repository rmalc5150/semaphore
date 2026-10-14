# Historical scope: January 1, 2021

The user selected **2021-01-01, inclusive**, for all historical data capture on
September 24, 2026. The shared setting is
[`config/historical-collection.json`](config/historical-collection.json), read
by `historical_policy.py`. It applies across all agreed sectors and geographies.

September 24 revision: all migrated historical collectors now default to
**2021-01-01**. This supersedes the earlier patent-only cutover. The patent
runner pins the same date in `config/patent-backfill.json`;
`config/model-data-policy.json` records the HMM/TFT start and requires verified
coverage and point-in-time feature availability. Model dataset enforcement
remains to be implemented. Existing evidence and Athena partitions are retained.

Implemented defaults cover the shared SEC, clinical/regulatory, disclosure and
patent historical CLIs, plus global patent query generation and backfill
planning, and Finlight/Marketaux shared news entry points. Clinical/regulatory adapters include ClinicalTrials.gov, FDA, EMA,
UK, Japan, ChiCTR and NMPA dated cohorts. Disclosure stages include HKEX,
documents, PR, licensing, M&A and strategic transactions.

Use a pinned **exclusive end** so retries retain their exact task/progress
identity. Existing explicit START END commands still work for bounded windows
and old checkpoints. Daily origins, lookbacks, completed runs, task versions,
universe assignments and previously published Athena releases are unchanged.
This setting does not retroactively filter or delete existing evidence.

```bash
# Plan all migrated sources, using the approved start and current universe.
.venv-athena/bin/python -B collect_historical.py \
  --config config/collection-operations.v0.3.json \
  --end-date 2026-09-23 --dry-run

# Plan the USPTO historical runner with the same start.
.venv-athena/bin/python -B patent_operations.py historical \
  --end 2026-09-23 --dry-run

# Generate a bounded first-month global patent query; no cloud access.
.venv-athena/bin/python -B patent_query_plan.py \
  --end 2021-02-01 --maximum-bytes-billed 50000000000 \
  --universe config/company-universe.v0.3.json \
  --output reports/patent-first-historical-month-2021.json
```

Standalone SEC, regulatory and disclosure commands support
`historical --end-date YYYY-MM-DD`. Standalone patent collection supports
`--mode historical --end YYYY-MM-DD`. Their omitted start now comes from the
shared policy. These standalone commands can fetch data; use the shared runner
with its window/page limits for large backfills. Daily patent collection still
requires an explicit start, and daily commands reject historical `--end-date`.

Sources still awaiting shared historical migration inherit the **2021 target**,
not a claim that bulk collection is operational. These include market
prices, people, conferences and social data. Their legacy exact-date or
recent-lookback commands retain their current semantics; a seven-day news query
must not be relabeled as years of coverage.

EODHD profiles, company/registry snapshots, and the NMPA inventory retain their
actual observation dates. Historical evidence dating from 2021 is requested
where supported; current snapshots cannot reconstruct their 2021 contents.
Complete patent-assignment chains may retain pre-2021 evidence needed to explain
later relationships. Undated source records and unavailable periods remain
explicit coverage gaps, rather than successful empty historical windows.

The original patent proposal was
`reports/patent-backfill-selected-2015-2026-09-24.json`: 141 monthly windows from
2015-01-01 through exclusive 2026-09-23, based on the existing verified coverage
report. The bounded global backfill runner is now implemented and its hourly
timer enabled. January–April 2015 are collected and published; the revised 69-window stream
starts January 2021 with separate progress and unchanged query limits. See
PATENT_BACKFILL_OPERATIONS.md. Each new query requires a fresh cost/source check.

Changing the shared date does not itself launch all backfills or reset the
ongoing daily jobs. Collection and Athena publication have separate completion
statuses. See PATENT_BACKFILL_PLAN.md and COLLECTION_OPERATIONS.md.
