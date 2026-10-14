# Clinical trials and regulatory migration — group 1

The seven existing scripts now accept `historical START END` and `daily [DATE]`
commands through `regulatory_collection.py` and `regulatory_sources.py`.
All seven sources now have completed records in the live Athena release.
ChiCTR contributed a complete 93-record daily window. NMPA contributed one
in-window record from an explicitly bounded three-ID verification cohort; this
proves the source path but does not represent complete NMPA registry coverage.
This is the first migration group, not completion of all remaining collectors.

## Live Athena pilot

Open the [Athena query editor](https://us-east-1.console.aws.amazon.com/athena/home?region=us-east-1#/query-editor)
in **us-east-1**, choose **optima-regulatory-pilot** as the workgroup,
**AwsDataCatalog** as the data source, and **optima_regulatory_pilot** as the database.

```sql
SELECT source, provider_id, title, event_date, date_basis
FROM optima_regulatory_pilot.clinical_trials
ORDER BY source, provider_id
LIMIT 50;
```

The `clinical_trials` table has **284 records**: 182 ClinicalTrials.gov studies,
8 CTIS trials, 93 ChiCTR trials, and 1 NMPA verification-cohort trial. These are
different source/date cohorts, not one synchronized historical snapshot. CTIS
events themselves are in `regulatory_events`. Native trial fields remain
available in `data_json`.

| Table | Rows | Meaning |
|---|---:|---|
| `research_records` | 407 | Latest observed state of each source record |
| `clinical_trials` | 284 | ClinicalTrials.gov, CTIS, ChiCTR, and bounded NMPA trial records |
| `regulatory_events` | 37 | 24 FDA events and 13 CTIS application/decision events |
| `regulatory_snapshots` | 86 | 61 UK MHRA rows and 25 Japan PMDA rows |
| `record_versions` | 407 | Distinct semantic versions, excluding retrieval-only changes |
| `record_observations` | 407 | Observations, raw-batch references and original source evidence |
| `record_companies` | 1 | One provisional Intuitive Surgical name match |
| `companies` | 20 | Shared provisional company universe |
| `company_sectors` | 20 | Shared sector assertions with review status and evidence |

The type-specific tables are subsets of `research_records`; do not add their
counts together with the parent table. Provider IDs are unique only within
their source. Join research records and company links using `record_id`.

No names were automatically verified as legal entities. Unknown sponsors are
retained for discovery instead of being discarded. The matching logic supports
all four sectors, including overlapping memberships, but these health and
regulatory sources cannot supply comprehensive semiconductor or energy-storage
coverage. Broader company discovery and the later patent/news collectors are
needed for that. Product IDs remain unresolved rather than invented.

All 407 `available_at` values are unknown. Event dates, source-update dates,
retrieval times and current company/sector assertions do not establish
historical model eligibility. This is a research release, not HMM/TFT training
features.

Inspect all source/type counts:

```sql
SELECT source, record_type, count(*) AS records
FROM optima_regulatory_pilot.research_records
GROUP BY source, record_type
ORDER BY source, record_type;
```

## Source status and date behavior

| Script | Live status | Historical and daily semantics |
|---|---|---|
| `clinicaltrials_studies.py` | Complete: 182 studies, including an intentional partial/resume test | Filters current study versions by last-update-post date; does not retrieve the version that existed at an earlier cutoff |
| `fda_drug_actions.py` | Complete: 24 approval events for June 3, 2024 | Filters approval submission dates and public complete-response letter dates; a CRL is not a permanent rejection, and letter date is not publication date |
| `ema_ctis_actions.py` | Complete: 8 trials and 13 events for September 17, 2026 | Public application submissions and decisions, with current trial details; confidential/pending material and unavailable past versions are not reconstructed |
| `uk_mhra_designations.py` | Complete: 61 current-list rows | Daily preserves the whole current ILAP/orphan snapshot. Historical filters known row dates; undated rows cause an explicit partial result instead of a claimed complete historical backfill |
| `japan_pmda_designations.py` | Complete: 25 current-list rows | Daily preserves the current SAKIGAKE list; historical selects designation dates within the requested interval from that current list |
| `chictr_studies.py` | Complete: 93 trials registered September 17, 2026, with resumed pages and evidence in S3 | Registration-date discovery; current record count drives pagination, with descending-date checks. Older windows require reconciliation to observe changes |
| `nmpa_drug_trials.py` | One verified record from an explicit three-ID cohort is live in Athena | Dates come from detail pages. Listing order is registration number, not disclosure date; unfiltered date-window collection requires full pagination. Cohort completion is not full-registry coverage |

CTIS search stops with a partial status when it reaches its public 10,000-result
limit before covering the requested range. openFDA stops with a partial status
if its supported offset limit would be exceeded. Large ranges may therefore
need additional source-specific partitioning before they can be declared
complete. Historical commands split at month boundaries without expanding the
requested start or exclusive end.

These APIs do not offer transactionally frozen multi-page snapshots. Totals,
revision metadata where available, duplicate identities, token cycles and
sort changes are checked, but unchanged counts cannot prove the source did
not change during collection. Every successful response is saved as evidence.
ClinicalTrials.gov supplies its total on the first page only; subsequent
pages are checked against that initial total.

The current ChiCTR page also advertises historical-version links. Retrieving
and validating that history is separate work; this adapter currently collects
the current detail pages only.

Reference documentation: [ClinicalTrials.gov fields](https://clinicaltrials.gov/data-api/about-api/study-data-structure),
[openFDA pagination limits](https://open.fda.gov/apis/query-parameters/),
[public CRL coverage](https://open.fda.gov/apis/transparency/completeresponseletters/),
[CTIS transparency rules](https://www.ema.europa.eu/en/human-regulatory-overview/research-development/clinical-trials-human-medicines/clinical-trials-information-system).

## Run collection

Use the isolated Python 3.12 environment and `requirements-research.txt`.
The new commands default to `config/collection-storage.s3.json`, writing under
`s3://data-collection-059416028963-us-east-1-an/research-data/`.

```bash
# Historical: June 3 inclusive, June 4 exclusive.
.venv-athena/bin/python -B clinicaltrials_studies.py historical 2024-06-03 2024-06-04

# Daily: explicit completed source-calendar date, with UTC cutoff validation.
.venv-athena/bin/python -B ema_ctis_actions.py daily 2026-09-17

# Bounded attempt. A limit before exhaustion produces partial, not complete.
.venv-athena/bin/python -B clinicaltrials_studies.py historical 2024-06-03 2024-06-04 \
  --page-size 100 --max-pages 1

# Resume using identical window, filters and page size; raise/remove max-pages.
.venv-athena/bin/python -B clinicaltrials_studies.py historical 2024-06-03 2024-06-04 \
  --page-size 100

# Re-query a completed daily date plus seven preceding days for late publication.
.venv-athena/bin/python -B fda_drug_actions.py daily 2026-09-17 \
  --lookback-days 7 --refresh
```

Repeat the exact command without `--refresh` to resume an unfinished attempt.
`--refresh` deliberately restarts the task from the source. Page size is part
of task identity. Daily without a date selects the preceding UTC day; it does
not automatically catch up arbitrary missed dates. Use explicit dates for
recovery when using individual scripts. The shared runner provides catch-up
and recent-date reconciliation; see COLLECTION_OPERATIONS.md.

Default `--selection all` retains unmatched discovery records. To select only
candidate matches to companies in a particular configured sector:

```bash
.venv-athena/bin/python -B clinicaltrials_studies.py daily 2026-09-17 \
  --selection universe --sector robotics
```

Sector selection uses current configured memberships, not verified historical
classifications. The four choices are `biotech`, `robotics`, `semiconductors`,
and `energy_storage`; storage includes the full agreed taxonomy.

`--backend local --output-root PATH` selects local output. `OPENFDA_API_KEY` is
optional and supplied at runtime; the previous literal key has been removed.
China sources use the existing Decodo/Secrets Manager integration. Credentials
are excluded from stored request URLs, checkpoint scope and printed errors.

### Chinese registry verification (September 18, 2026)

The live NMPA listing advertised 36,617 records across 1,831 pages. Waiting for
the actual HTML table resolved the previously blank/verification-only responses
in successful tests. Direct `currentpage=2` returned the second page; the adapter
now validates the displayed page number instead of replaying next-page clicks.
The official `clinicaltrials.searchlistdetail.dhtml?reg_no=CTR...` endpoint
provides detail records even when listing links use JavaScript. Registration
numbers are checked against detail fields; dates and trial status are parsed
as separate fields. Registration-number year is never substituted for a
disclosure date. Sponsor matching excludes contact-person labels.

ChiCTR's formerly generic error was identified as an intermittent **target
HTTP 405**. Gateway and target failures now have distinct safe reason codes.
Rendered requests wait for a table (the specific listing/detail table for NMPA),
retry transient failures and incomplete HTML bodies at most four
attempts, and permit one reload for a target 405. Verification pages still stop
collection. A failed source attempt writes `failure.json` beside its final
manifest, with public URL/status diagnostics, saved evidence references, and
the last committed cursor. Credentials and gateway response bodies are not
included. Detail batches in subsequent runs use at most three concurrent
requests; their record order and checkpoint boundaries remain deterministic.

To reproduce the explicitly scoped NMPA test:

```bash
.venv-athena/bin/python nmpa_drug_trials.py historical 2022-06-28 2022-06-29 \
  --registry-id CTR20221481 --registry-id CTR20221465 --registry-id CTR20221557
```

All three details were fetched; only CTR20221481 fell in that date window.
The first complete verification manifest is
`manifests/collection_runs/source=nmpa_trials/dataset=research_records/run_b8dcf859-4e17-460b-89e8-3da075d99829/final.json`.
Its scope contains the exact sorted ID list and an explicit coverage caveat.
Its watermark cannot advance an unfiltered registry task. Source HTML for
out-of-window cohort members is retained in input evidence.

The final-code rerun also completed:
`manifests/collection_runs/source=nmpa_trials/dataset=research_records/run_4c12b3c6-8a3c-46f0-b071-629660a2086d/final.json`.
Its S3 evidence checksums, source schema, and curated trial row were verified:
CTR20221481, disclosure date June 28, 2022, one company name, and unknown
historical availability. `china-verification-status.json` records that check.
The ChiCTR continuation completed as
`run_f510d7f6-5ded-43dd-bbe0-fa96d0acaca8`, with 93 records for the full
September 17 window (exclusive end September 18). Its earlier partial attempts
remain as immutable run history. Full NMPA history and recurring daily
reconciliation have not been completed. A practical full-registry baseline
must first freeze an observed registration-ID inventory and then fetch details
in bounded cohorts; otherwise a changing 36,000-plus-record listing can shift
while a multi-day scan is in progress.

The old `day`/`week`/`month` interfaces retain their previous behavior for
compatibility. `collect_daily.py` and `collect_historical.py` now use shared
paths and universe 0.2.0. Their scope, dependency behavior and unmigrated
sources are described in COLLECTION_OPERATIONS.md. To resume an old direct
regulatory task, pass its original universe explicitly with --universe.

## Storage, resume and curation

Raw records are JSONL under `raw/source=<source>/dataset=research_records/`.
Source JSON, HTML, CSV, spreadsheets and PDF bytes are stored by SHA-256 under
`source_documents/<source>/`. Immutable input receipts record response
references, provider identities and cursors. Shared manifests/checkpoints
record complete, partial or failed outcomes. Errors and caps do not advance
watermarks. UK historical collection does not overwrite a mutable daily
snapshot or synthesize added/removed events.

Only explicitly selected, committed, complete runs are eligible for curation.
The curator checks configuration hashes, raw bytes/counts, record schemas,
scope and source evidence checksums. Resumed records retain their original
run IDs. Version identity excludes retrieval-only evidence changes; content,
matching and temporal changes remain distinct versions.

The published release is
`8e56cfc6d75997e9e92b08fa31d2c06c4406d90616a3e52ffca7c2e999e081f3`.
Find it locally in `regulatory-athena-build/<release_id>/` and in S3 under
`research-data/curated/regulatory_pilot/releases/<release_id>/`.
The S3 release contains the nine Parquet tables, SQL, release manifest, and
successful query verification records. It is immutable: new collections do
not automatically replace these tables.

```bash
.venv-athena/bin/python -B regulatory_athena.py prepare
.venv-athena/bin/python -B regulatory_athena.py publish --release-dir regulatory-athena-build/RELEASE_ID
.venv-athena/bin/python -B regulatory_athena.py deploy --release-dir regulatory-athena-build/RELEASE_ID --update-existing
```

`config/regulatory-athena-pilot.json` selects seven complete source manifests.
Publication verifies S3 bytes before registering tables. The shared deployment
code supports separate SEC and regulatory databases; it refuses to overwrite
an unrelated table or a table pointing at a different release. Athena uses a
dedicated workgroup, encrypted query output and a 100 MiB scan limit per query.

## Validation and remaining work

The collection, storage, contract, SEC, regulatory and Decodo suites passed
125 tests after the Chinese registry fixes, including retry bounds, safe
diagnostics, cohort resume/scope isolation, paired NMPA fields, and rejection
of wrong trial identities or ignored page parameters. Four live Athena queries
verified all 407 records, nine table counts, source/type counts and unknown
availability timestamps. The current count query ID is
`c772c0be-a0f8-454d-9209-71dd951fca8b`; full results are in
`athena-verification.json` in the local release and `verifications/` in S3.

Remaining group-one work: expand the verified NMPA cohort into a practical
complete baseline and daily reconciliation flow;
expand provider-specific historical reconciliation and large-range CTIS
partitioning. Chinese live access is verified; complete registry coverage is not claimed. Subsequent groups
cover other disclosures and derived collectors, patents/news/market data,
people/partnerships/conferences/discovery, and finally the coordinated runners.

## NMPA full-baseline inventory

`nmpa_baseline.py` separates listing discovery from expensive detail retrieval.
The first live checkpoint for the September 22, 2026 inventory committed 20
registration IDs. At that observation NMPA advertised 36,662 records across
1,834 pages. The supporting run is
`run_e1100b07-0e2a-43ba-8227-491305c2631c` in dataset `registry_inventory`.

The inventory records each observed registration number, title, detail URL,
listing page, advertised totals, and source-document hash. Pagination can be
resumed without re-fetching committed pages. Because the public listing is not
a transactionally frozen snapshot, completion means all pages advertised by
the final response were visited. A later reconciliation snapshot is required
to identify records added or shifted during the scan.

```bash
# Resume at most 110 listing pages; expected page_limit is a successful bounded run.
.venv-athena/bin/python -B nmpa_baseline.py inventory 2026-09-22 --max-pages 110

# After the inventory manifest is complete, freeze deterministic 200-ID cohorts.
.venv-athena/bin/python -B nmpa_baseline.py plan \
  --manifest-key manifests/collection_runs/source=nmpa_trials/dataset=registry_inventory/RUN_ID/final.json \
  --cohort-size 200
```

The prepared `optima-nmpa-inventory.timer` runs daily at 04:00 UTC with up to
15 minutes of jitter and resumes 110 pages per invocation. It is ordered after
the EODHD profile service when both are activated together. The fixed inventory
date is intentional: changing it would create a new task instead of resuming
the current baseline. Detail cohorts and recurring addition/change
reconciliation are enabled only after this inventory completes and validates.

## NMPA rendered response repair, September 27

The public NMPA listing can return target HTTP 202 even when browser rendering
has produced the requested page. Inventory collection now passes a strict
pending-response validator to the scraper. It requires the requested page number,
registration rows, matching totals/page count, the expected row count and no
within-page duplicate IDs. Other HTTP 202 responses remain retryable failures.
Verification pages still stop collection, and accepted HTML is saved as source
evidence before inventory records are committed.

NMPA requests now use the scraper's default geographic routing; the China override
returned an empty page shell during validation. A default-route response for page
88 supplied 20 rows, 1,836 pages and 36,708 advertised registrations. These are
current observations, not proof of a frozen historical registry. Other regulatory
sources retain their configured China routing and default HTTP status checks.
