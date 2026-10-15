# Patent collection migration

The production migration entry point is `patent_collection.py`. The older
`uspto_patents.py`, `patent_landscape.py`, `patent_bigquery.sql` and
`patent_events.py` remain compatibility/pilot utilities. They are not scheduled
production collectors. In particular, the old snapshot event differ must not be
used for model features: a detected change is not proof of a dated assignment.

The new collector uses the shared v0.2 company universe, immutable raw JSONL,
source response hashes, resumable checkpoints, and complete/partial/failed run
records. Company name matches nominate candidates only. They do not establish
ownership, subsidiary consolidation, or historical identity. Patent technology
classifications are independent of company-sector memberships.

Rules in `config/patent-classification.v1.json` cover biotech, robotics,
semiconductors, batteries, supercapacitors, thermal storage, mechanical storage,
and hydrogen storage. These are review heuristics with explicit CPC/text hits,
not calibrated probabilities or an assertion of exhaustive recall. Unknown
companies and unmatched patents are retained for discovery. Non-Latin company
names are preserved. No patent is assigned to a product without evidence.

## S3 organization

Bucket: `data-collection-059416028963-us-east-1-an`.

- `research-data/incoming/patents/google-bigquery/`: original global exports.
- `research-data/source_documents/google_patents_bigquery/`: hashed export evidence.
- `research-data/source_documents/uspto_odp/`: hashed API response evidence.
- `research-data/raw/source=<source>/dataset=patent_records/`: normalized JSONL.
- `research-data/manifests/collection_runs/source=<source>/dataset=patent_records/`: immutable attempts.
- `research-data/checkpoints/`: durable task checkpoints.

The inbox convention is `<export-date>/<job-id>/part-00000.jsonl`, alongside
`export-metadata.json`; see `config/patent-export-inbox.json`. S3 stores the files;
executing BigQuery still requires a configured Google Cloud project and billing.
There is no automatic inbox watcher. `patent_bigquery_collection.py` now queries
BigQuery directly from EC2 and writes both original JSONL export pages and shared
research records. It is not scheduled for recurring execution.

## Historical and daily USPTO runs

```bash
.venv-athena/bin/python patent_collection.py uspto \
  --mode historical --start 2025-01-06 --end 2025-01-07 \
  --page-size 50 --max-pages 50

.venv-athena/bin/python patent_collection.py uspto \
  --mode daily --start 2026-09-21 --end 2026-09-22 \
  --page-size 50 --max-pages 10
```

End dates are exclusive. Historical discovery uses filing dates; daily discovery
uses the API's `lastIngestionDateTime`, which catches updates to older filings.
The provider does not return a timezone for that field, so windows denote provider
calendar days. This is a provider-index update time, not a public event time.
Both modes retain current application snapshots and source event lists; a
historical search cannot reconstruct what all fields looked like on the filing
date. `available_at`, `event_at`, and `source_updated_at` remain unknown.

The stored USPTO Secrets Manager key is loaded at runtime and sent only in the
authentication header. Responses and nonsecret request parameters form evidence.
API requests are paced and transient failures receive bounded retries.

Re-run the same command to continue a partial run. `--max-pages` bounds work per
invocation and is not part of task identity. Changing page size, date window,
universe or classification rules starts a separate task. Do not run two workers
for the same task. A completed task is skipped; use `--refresh` deliberately to
restart it. A changed source result count requires refresh, because offset
pagination against a mutable index cannot prove the same snapshot. Sorted IDs,
page sizes and date filters are checked before checkpoint advancement. Matching
counts still cannot guarantee snapshot isolation; overlapping reconciliation is
needed when scheduling is added. No global collection watermark is advanced.

Exit 0 means this task is complete; exit 2 means partial or a recorded source
failure. Other exceptions return exit 1. A partial run never claims completeness.
The date search currently retrieves all returned US applications, then attaches
sector/company candidates locally. A live daily probe found 68,553 applications
for September 21, 2026; budget and throughput must be measured before enabling a
timer. Existing SEC/regulatory job identities and schedules are unchanged.

## Global export imports

```bash
.venv-athena/bin/python patent_collection.py import --input patents.jsonl \
  --mode historical --start 2025-01-01 --end 2025-02-01 \
  --date-basis filing_date --page-size 50 --max-pages 10
```

Use `--backend local --output-root /tmp/patent-import` for offline validation.
For new exports use `--date-basis publication_date`; both historical and daily
imports support explicit windows. Split large exports into files under 256 MiB.
Every row must have a valid publication identity and a date within the supplied
window. Exact normalized duplicates are removed; conflicting versions remain.
The original file is preserved byte-for-byte. Existing `matched_company` fields
are not trusted as identity assertions.

The saved pilot export has 385 rows across 13 publication authorities, including
62 CN publications. Its original job metadata and publication dates are missing.
The importer records that limitation and keeps availability unknown. The 385-row
export is not a comprehensive China or worldwide patent backfill.

`patent_discovery.sql` replaces fixed 20-company discovery for future exports.
`patent_query_plan.py` generates named parameters from the shared universe and
all technology rules, including technology discovery outside known companies:

```bash
.venv-athena/bin/python patent_query_plan.py \
  --start 2025-01-01 --end 2025-02-01 \
  --maximum-bytes-billed 1000000000 \
  --output reports/patent-bigquery-dry-run.json
```

The byte limit is a ceiling, not an estimate. The generated `configuration` is
a BigQuery dry-run job configuration; `provenance` is a separate local audit
object, not an API job field. No job is submitted by this script. Validate the
current source schema/freshness and dry-run cost after project access is set up.
Use periodic overlapping publication windows for lagging global source updates;
do not assume the global source refreshes daily.

## Remaining rollout

The full January global review is now live in nine Athena tables. See
`PATENT_ATHENA.md`: 78,542 publications, 54,370 with CPC-supported technology
sectors, 3,459 with supported reported-party name links, and 23 official US
assignment histories with 29 events. Four depositary-receipt relationships are
reviewed separately from company identity and patent title. `PATENT_REVIEW.md`
documents source evidence and unresolved cases. These statuses do not establish
current ownership or model eligibility; recurring publication is not scheduled.

Live validation on September 22, 2026:

- Completed global export import: 385 observations,
  `run_ea515d1f-e965-4440-a4ca-d05a673e124c`.
- Completed USPTO January 6, 2025 filing-date sample: 2,272 observations,
  `run_39356c26-e106-4e0c-80d0-285fa8cc0b85`. The run resumed across bounded
  attempts and includes PCT applications returned by the USPTO source.
- Daily September 21 sample: 50 observations, partial at the configured page
  limit, `run_16bde593-3080-47e6-8778-ecfc8706a8e9`. This is not a complete day.
- `unused/reports/patent-migration-review-2026-09-22.json` verifies committed manifests,
  configuration hashes, source evidence and all 2,657 completed observations.
  It contains 425 observations with company candidates. All remain subject to
  identity review; 1,013 lack publication dates and none is marked eligible for
  point-in-time model features. These initial legacy/USPTO discovery samples are
  not included in the later January global Athena publication.
- 78 relevant patent, storage, runner and regulatory-curation tests passed.

Google Cloud project `patent-research-508613`, number `24037405713`, is connected
to EC2 using Workload Identity Federation. See `GOOGLE_PATENTS_ACCESS.md` for
verified access, costs, and source freshness. The September 22 publication-date
check found newest CN publication April 10, 2026 and US publication April 21,
2026. The September 23 revision has now been measured: CN reaches September 8
and US September 17. See PATENT_BACKFILL_PLAN.md for the full evidence. Complete
global daily coverage is not established.

Run the prepared January 2025 global publication window with a 50 GB billed-scan
ceiling (approximately $0.28 before free allowance/credits):

```bash
.venv-athena/bin/python patent_bigquery_collection.py \
  --plan reports/patent-bigquery-dry-run.json \
  --maximum-bytes-billed 50000000000 --max-pages 100
```

Re-run this exact command to continue downloading the same job's results after
a partial run. The durable checkpoint stores the job ID before submission, so
retrying does not deliberately launch another billed job. Only `--refresh`
starts a new job for a completed task. Original JSONL pages and per-file hashes
are written to the S3 inbox, while normalized records use the shared raw layout.
Final export metadata records query parameters, universe/rules provenance and
BigQuery job statistics. Curate only the committed complete manifest.

Resume requires BigQuery to still retain the job results. If they expire before
download completes, a deliberate refresh and another bounded query are needed.
No timer has been enabled for paid global queries. A September 23 metadata check
found a newer source revision; its country publication-date coverage and cost
checks are now saved in PATENT_BACKFILL_PLAN.md and the linked reports.
The bounded USPTO daily runner and free global metadata monitor are documented
in [PATENT_OPERATIONS.md](PATENT_OPERATIONS.md).

1. Maintain global query/export provenance and resolve the source's freshness gap.
2. Review representative company and technology matches in all four sectors,
   especially Chinese names, subsidiaries and storage subcategories.
3. Measure throughput, choose cohort limits, and integrate scheduled catch-up and
   reconciliation without changing existing collectors' progress identities.
4. Extend the verified Athena pilot to recurring, incremental publication from
   committed complete manifests, preserving versions and expanding flattened
   filing/priority/family metadata beyond the current reviewed publication fields.
5. Derive dated patent events only from source-supported dates, with observed
   changes separate from legal events. Validate point-in-time eligibility before
   using patent features in HMM/TFT training.

## Examination and petition extension

Implemented October 14, 2026. `patent_collection.py office-actions` and
`patent_collection.py petition-decisions` delegate to `patent_prosecution.py`.
They write separate `uspto_odp` datasets `patent_office_actions` and
`patent_petition_decisions`, governed by
`schemas/patent-prosecution-payload.schema.json` and the shared envelope contract.
Search JSON, document metadata and original PDFs are retained with checksums.
Failed downloads leave durable document-task receipts and keep their source page
partial; retries reuse successful downloads. Provider text and structured fields
are preserved; model-extracted claims remain empty until an extractor is implemented.

The live pilot began at January 1, 2021, using source submission/decision dates,
including in-range documents for older applications. Final petitions are filtered
with `finalPetitionDecisionIndicator:true`. Office Action text results can include
allowance notices and other document codes; the dataset name is not itself proof
of a rejection. Current patent snapshots remain intact and are enriched through
application and official-document joins rather than replaced.

See [prosecution operations](PATENT_PROSECUTION_OPERATIONS.md) for the enabled
historical/incremental collector, limits, reconciliation and independent coverage.
All USPTO application and prosecution requests now use a shared host request gate,
with at least two seconds between reserved API request starts. Typed observation
publication is integrated into `research_publication.py`; partial windows are not
published. Both proposed discovery routes consume these observations as evidence.
