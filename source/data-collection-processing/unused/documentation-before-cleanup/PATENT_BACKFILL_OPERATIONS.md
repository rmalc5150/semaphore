# Global patent backfill operations

`patent_backfill.py` collects monthly global patent candidates from the approved
patent-specific start **2021-01-01**, read from `config/patent-backfill.json`.
The shared historical default for all migrated sources is also 2021-01-01.
The initial end is pinned at **2026-09-23 exclusive**. This is 69 windows,
including the partial final September window. It uses universe 0.3.0 and the
existing company-name OR technology-rule discovery across all four sectors.

`config/patent-backfill.json` controls execution:

- One monthly window per invocation; finish its result download before the next.
- Up to 100 result pages of 500 records per invocation. A partial invocation
  resumes the same job and page token, with raw batch integrity validation.
- At most four newly submitted job identities per UTC day, reserving up to
  200,000,000,000 billed bytes across them. Each query has its own hard
  50,000,000,000-byte ceiling and a fresh dry-run/source metadata check before
  its first submission. Existing job downloads do not consume another slot.
- Reservations are recorded in S3 before submission. Ambiguous requests reuse
  their fixed job ID. If resubmission crosses UTC midnight it also reserves
  capacity for the new day. Uncertain/orphaned reservations are not reclaimed.
- Missing jobs older than 20 hours, and unavailable/expired query results, stop
  with an explicit failure. The runner never refreshes into a replacement paid
  job automatically. New queries require the previous window to be complete.

These limits cover this runner, not the entire Google billing account or other
manual scripts. Budget-limited invocations remain partial until the next UTC
day. Above-ceiling estimates remain partial pending a smaller scan or a reviewed
configuration change. Provider errors cannot advance the completed date.

At four new windows per day, 69 windows require at least **18 quota days**, with
additional time possible for EC2 downtime, limits, errors or incomplete downloads.
The page and daily limits are configurable; raising a daily limit alone does
not raise the per-query cap or rewrite window identities. Keep the pinned end,
universe, rules, page size and query ceiling unchanged while resuming this run.

The systemd unit `optima-patents-backfill.timer` runs hourly at minute 10 UTC,
with up to five minutes of jitter. It is persistent across EC2 restarts; S3
progress determines where collection resumes. The service runs as `ec2-user`,
has a three-hour timeout and accepts exit 2 for bounded partial work. Failed
attempts exit 1. A dedicated local lock prevents overlapping invocations of
this backfill runner. Daily USPTO and other collectors retain their own jobs.
This is a single-EC2 runner, not a distributed multi-worker scheduler.

```bash
# No cloud calls or writes.
.venv-athena/bin/python -B patent_backfill.py --dry-run

# Read S3 progress; no provider query.
.venv-athena/bin/python -B patent_backfill.py --status

# Resume one bounded window manually when no scheduled invocation is active.
.venv-athena/bin/python -B patent_backfill.py --max-pages 2

# Verify the latest completed window's raw data and source evidence in S3.
.venv-athena/bin/python -B patent_backfill.py --audit \
  --output reports/patent-backfill-audit.json

systemctl list-timers optima-patents-backfill.timer
journalctl -u optima-patents-backfill.service -n 20 --no-pager
```

`--status` and `--audit` use the same lock and may report `runner_already_active`;
the journal shows page-level progress while collection is running. Audit reads
all batches/evidence in the latest complete window and verifies hashes, counts,
unique observation IDs, publication dates and export metadata. It is separate
from company/sector adjudication and is not an Athena publication operation.

S3 keys under the existing `research-data/` prefix:

- `operations/patents/global-backfill/streams/<stream>/progress.json`
- `operations/patents/global-backfill/streams/<stream>/plans/`
- `operations/patents/global-backfill/streams/<stream>/attempts/`
- `operations/patents/global-backfill/streams/<stream>/audits/`
- `operations/patents/global-backfill/jobs/<job-id>.json` (estimate/source evidence)
- `operations/patents/global-backfill/budgets/<UTC-date>.json`

The active 2021 stream is
`f80276b540a3f85eecc0e748099faa1d2664766b4933827652aedbca4f9dd8af`.
The preserved 2015 stream is
`11667a029bde4147814002bc7c7ba51c318f9c56313601b84819371c56ce8301`;
use `--config config/patent-backfill.2015.json --status` to inspect it.
January–April 2015 contain 164,690 collected and verified publications.
Their S3 evidence, checkpoints and Athena partitions remain available.
The revised stream has independent collection/publication progress but shares
the same daily query reservations, so the cutover does not renew the budget.
September 24 already used all four job slots; 2021 collection must wait for
the next UTC day. Both existing timers read the active config each invocation.
Raw JSONL, source evidence and immutable manifests retain the shared layout;
original export pages also appear under `incoming/patents/google-bigquery/`.
Different months may reflect different source revisions; this is not a frozen
worldwide snapshot. Undated source records remain a separate discovery gap.

The January 2015 live validation saved **37,738 candidates**, resumed from an
initial 1,000-record partial attempt using the same BigQuery job, and advanced
the next date to February 1 only after the committed manifest was complete.
The complete manifest is
`manifests/collection_runs/source=google_patents_bigquery/dataset=patent_records/run_e353700c-46c3-4417-a9ec-7b8d1d4e45fd/final.json`.
See `reports/patent-backfill-first-month-audit-2026-09-24.json` for read-back
verification. Relevant offline tests: **92 passed**.

January 2015 has now passed policy review, curation and live Athena verification:
37,738 publications are queryable through four new monthly backfill views. See
[PATENT_BACKFILL_ATHENA.md](PATENT_BACKFILL_ATHENA.md) for queries and the repeatable
publication commands. Unresolved identities and ownership remain explicit.
Automatic publication is enabled through `optima-patents-publication.timer`.
It checks completed collection checkpoints every ten minutes and publishes one
month per invocation, advancing separate publication progress only after Athena
verification. Failed publications retry independently of collection. The January
2025 pilot is preserved. See PATENT_BACKFILL_ATHENA.md for publication status.
