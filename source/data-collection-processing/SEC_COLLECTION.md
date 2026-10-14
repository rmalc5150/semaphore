# SEC collector migration — step 3

The new `sec_filings.py historical` and `sec_filings.py daily` commands use
the shared contract, JSONL writer, manifests, checkpoints, and watermarks.
They collect filing metadata and complete-submission links from SEC quarterly
master indexes. Full filing documents, acceptance timestamps, and business-event
extraction are not downloaded by this stage.

Implementation, offline tests, and a bounded live S3 pilot are complete. The operator-supplied
bucket is configured in `config/collection-storage.s3.json`, using the
`research-data/` prefix. The SEC contact header is saved in `config/sec.env`.
Live collection uses the EC2 instance role credentials. The sandbox
blocks the instance metadata service, causing SDK credential discovery to
return `NoCredentialsError`. Live checks must run in an environment that can
reach instance metadata; credentials do not need to be copied into config.
The read-only check outside the sandbox succeeded using the `iam-role`
credential provider: `HeadBucket` returned HTTP 200 and confirmed `us-east-1`.
The subsequent live collection saved source evidence, records, and run metadata.

## Live pilot results

Historical and explicit daily mode each completed the window June 3, 2024
(exclusive end June 4). Each saved 11 records: biotech 5, robotics 3,
energy storage 2, and semiconductors 1. All are provisional name-based matches,
not verified company identities. The two runs cover the same 11 accessions;
they represent separate observations, not 22 distinct filings.

- Historical run: `run_017c2a87-e157-4cef-be58-8342cb6d2418`.
- Daily run: `run_7ee91d44-3360-467f-8dde-c2852adbe076`.

Final manifests are under
`research-data/manifests/collection_runs/source=sec_edgar/dataset=filings/<run_id>/final.json`.
S3 read-back verified record schemas, batch byte counts and SHA-256 hashes,
source snapshot hashes, accession identity agreement, committed complete
manifests, and both watermarks at `2024-06-04T04:00:00Z`.

The first attempt (`run_cb29ee1d-cfc1-419c-ab11-ade4e9be582b`) remains recorded
as failed with no filing records. It exposed a parser assumption that an index
must end with a newline. Version `sec-index-1.1` accepts a valid final row
without that newline and retains row/transport validation. All 74 offline tests
pass, including the regression test. No recurring schedule was installed.

## Source and date semantics

The source is `https://www.sec.gov/Archives/edgar/full-index/YYYY/QTRn/master.idx`.
The collector preserves exact index bytes, SHA-256, retrieval time, declared
last-data-received date, and selected-file counts. One invocation reuses a
quarter's downloaded snapshot across its bounded windows. Only one quarter's
parsed index is cached in memory at a time during multi-year backfills.

SEC documents nightly index updates and later corrections, including weekly
rebuilds of full/quarterly indexes. Indexes expose filing dates, CIKs, names,
forms, and paths; they do not establish precise publication times of every
version. Accession numbers identify submissions; their first ten digits can
identify a submitting agent rather than the issuer. CIKs are not recycled.
See [SEC's access documentation](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data).

Input ranges use New York calendar days: **start inclusive, end exclusive**.
They convert to exact UTC boundaries using daylight-saving rules. Only completed
days from 1994-07-01 onward are accepted. Historical ranges split at month
boundaries; daily ranges split by day. Explicit dates are never expanded to
whole months.

The parser checks the header and every row, rejects unexpected quarter dates,
invalid paths, invalid CIKs/dates, and malformed data, and removes exact duplicate
rows. A valid final row may omit its trailing newline, as observed in the live
SEC index. Malformed final rows and HTTP bodies inconsistent with declared
content length fail validation. These checks do not prove the source contains every
historical filing that ever existed.

The last-data-received header must cover the requested weekdays. Weekend gaps
beyond that date are allowed. Unknown weekday gaps, including a holiday not yet
covered by a later index, produce `partial/index_coverage_incomplete`; they are
not reported as zero filings. Missing indexes are partial, and invalid source
data fails the run. Complete means this snapshot/query was exhausted, not
verified global-company coverage or point-in-time historical truth.

## Company selection and record meaning

Default selection is the enabled shared universe across all four sectors.
Repeatable `--sector`, `--company-id`, `--cik`, and `--form` filters narrow it.
CIK and form filters intersect the other selection rules. Use
`--selection all --cik NUMBER` to select an issuer independently of the universe.
`--selection all` without a CIK retains all filings, including unresolved ones.

Confirmed matching requires a unique, verified `sec_cik` external identifier
on a verified legal entity. CIKs normalize to ten digits. Names and aliases
can nominate candidate matches, but do not establish identity. Candidate IDs
stay in the payload, not in the envelope's `company_ids`. Normalization retains
non-Latin characters and does not collapse distinct foreign names to empty
strings. Rejected companies/aliases are excluded; rejected sector assertions
are not used to satisfy a sector filter.

The actual 20-company pilot remains provisional with no verified CIK mappings.
Its name matches are candidates, not confirmed entities. No selected filing
for an unmapped company is not proof that it had no filings. Missing old names,
subsidiaries, and non-SEC filers remain coverage limitations. Global scope here
means any relevant SEC filer, including foreign/private filers; this source is
not a substitute for every country's disclosures.

CIK matching identifies entities; it does not make current sector membership,
ownership, or aliases eligible at an earlier model cutoff. Sector filtering
uses the configured universe, not a reconstructed historical universe.

One record represents one accession. Multiple issuer rows sharing it are
retained together, with all resolved company IDs. Conflicting form/date values
for one accession fail the run. Separately accessioned amendments retain
separate record identities.

`event_at` is the date filed, at day precision in America/New_York.
`available_at` and `source_updated_at` remain unknown: filing/retrieval times
are never substituted for public availability. Original source retrieval time
is retained as `ingested_at` on a pinned-snapshot resume. Resumed attempts have
new run IDs while earlier pages retain their original IDs.

A final `selection.json` reports confirmed, candidate-only, and unmatched filing
counts, counts by configured sector including candidates, and selected companies
with no filing match. Sector counts overlap for multi-sector/cofiled records
and are not historical classifications.

## Live operation

Load the operator-supplied organization name and contact email before running:

```bash
source config/sec.env
```

This sets `SEC_USER_AGENT` to `Optima Holdings support@optima-holdings.com`.
The collector rejects missing/example contact headers. It paces requests at
four per second per client, with bounded transient retries. Coordinate total
traffic across processes. SEC requests a declared organization/contact header
and currently limits traffic to ten requests per second across a user.
[SEC fair-access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)

Local output from live SEC data:

```bash
python3 sec_filings.py historical 2024-06-01 2024-07-01 \
  --backend local --output-root ./sec-output
```

For the configured S3 destination, pass the storage config explicitly:

```bash
python3 sec_filings.py historical 2024-06-03 2024-06-04 \
  --storage-config config/collection-storage.s3.json
```

This writes under
`s3://data-collection-059416028963-us-east-1-an/research-data/`.
The default example config still uses local output. AWS uses the normal
credentials chain; no credentials belong in the config or task scope. See
`COLLECTION_STORAGE.md` for overrides. The collector does not create buckets
or policies.

First automatic daily run, with a stable explicit origin:

```bash
python3 sec_filings.py daily --origin 2024-06-01 \
  --backend local --output-root ./sec-output
```

Subsequent runs resume from the contiguous boundary and refresh the preceding
three calendar days by default:

```bash
python3 sec_filings.py daily --overlap-days 3 \
  --backend local --output-root ./sec-output
```

Use the same output config, universe, and filters. They determine stream
identity; changing scope/universe starts a new stream and requires an initial
daily origin. With zero overlap, a caught-up stream returns `up_to_date`.
Explicit `daily YYYY-MM-DD` selects one day; use `--refresh` to recollect it.
Overlap does not catch every older correction: periodically refresh older
windows when those revisions matter. Daily/historical watermarks are separate.

## Resume and bounded pilots

Each attempt writes `input.json` beside its run manifests, pointing to an
immutable `source_documents/sec_edgar/year=YYYY/quarter=Q/<sha256>.idx`.
Once a page commits, resume uses those exact bytes, even if the SEC changes
the index. The cursor is a position in a deterministic selected-accession list;
cursor/count agreement is checked. Parser version, scope, and configuration
hashes participate in task identity.

Without committed pages, retries may fetch a newer index. This allows a delayed
nightly index to recover rather than pinning an incomplete header forever.
`--refresh` resets the active cursor and reads the source again, preserving
prior committed manifests.

`--max-records N` caps each window's current attempt. A truncated run is partial,
exits 2, and cannot advance a watermark. Rerun the same range/filters to resume;
page size and attempt limit may change. This cap does not reduce the quarterly
index download size. Use a short date range and specific CIK/form filters for
a small live pilot.

Exit codes: 0 for completed/up-to-date; 2 for a source-partial or source-failed
attempt; 1 for configuration/storage/runtime errors. Printed JSON and manifests
distinguish partial from failed. Source failure stops later windows. Complete
out-of-order windows may report `watermark_status=coverage_gap_not_advanced`;
earlier gaps still need collection. A partial attempt is never a successful
stream boundary.

## Offline examples and verification

`examples/sec-filings/` holds fictional companies/CIKs and a synthetic index.
It covers four sectors, a duplicate row, a multi-issuer accession, and an
unmatched filer. These are not verified real company identifiers.
`--index-file` hashes the fixture into task identity and allows local output
only, preventing this mode from writing fictional records to S3.

```bash
# Intentionally partial: expect exit 2.
python3 -B sec_filings.py historical 2024-06-03 2024-06-08 \
  --index-file examples/sec-filings/master-2024-q2.idx \
  --universe examples/sec-filings/universe.json \
  --output-root /tmp/sec-step3-offline --max-records 2 --page-size 2

# Resume: expect five distinct accession records in total.
python3 -B sec_filings.py historical 2024-06-03 2024-06-08 \
  --index-file examples/sec-filings/master-2024-q2.idx \
  --universe examples/sec-filings/universe.json \
  --output-root /tmp/sec-step3-offline

python3 -B -m unittest test_research_contract.py test_collection_storage.py test_sec_filings.py
```

Tests cover source failures, malformed data, retry/pacing, strict date bounds,
empty results, all sectors, unresolved matches, multi-issuer accessions, snapshot
pinning, interrupted writes, daily overlap, and legacy command compatibility.
These are offline tests, not proof of live SEC access or AWS permissions.

## Compatibility and remaining work

`day` and `month` deliberately dispatch to `sec_filings_legacy.py`, preserving
the envelope and S3 paths consumed by `disclosure_event_collector.py`.
The coordinated `collect_daily.py` and `collect_historical.py` runners now use
shared paths, reviewed universe 0.2.0 and explicit document/event dependencies.
They accept exact dates and record source progress in S3. See
COLLECTION_OPERATIONS.md. Legacy direct day/month invocations remain available.

The bounded live validation is complete as described above. Real pilot CIK verification,
full document retrieval, and remaining collector migrations are separate work.
The first clinical/regulatory migration group now has all seven sources live in
Athena. ChiCTR has a complete daily window; NMPA remains limited to a verified
cohort while its full baseline is built. See `REGULATORY_COLLECTION.md`.
A bounded SEC-to-Athena curation pilot is now published and verified; see
`SEC_ATHENA_PILOT.md`. Broader incremental curation remains future work.
