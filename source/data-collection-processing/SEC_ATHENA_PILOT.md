# SEC-to-Athena pilot

This pilot turns the two successful June 3, 2024 SEC collection runs into a
small research dataset. It contains 11 distinct filings and preserves all 22
collection observations. These are filing metadata and submission links, not
the downloaded filing documents or model training features.

Status: **published and verified in Athena**. All six tables are registered,
and all five live validation queries succeeded. The local
`athena-pilot-build/<release_id>/athena-verification.json` and the corresponding
S3 verification record contain the returned rows and query execution IDs.

## Where to inspect it

- Region: **us-east-1**.
- Athena data source: **AwsDataCatalog**.
- Athena database: **optima_sec_pilot**.
- Athena workgroup: **optima-sec-pilot**.
- [Open the Athena query editor](https://us-east-1.console.aws.amazon.com/athena/home?region=us-east-1#/query-editor).
- [Open the curated S3 releases](https://s3.console.aws.amazon.com/s3/buckets/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data%2Fcurated%2Fsec_pilot%2Freleases%2F&showversions=false).

Select the workgroup, data source, and database above in the query editor.
The console identity you sign in with also needs permission to read these
resources; the collector runs using the EC2 instance role.

The current release is
`4f1b079c7071cd9a04246ce49f5bff6845cde2422ac79770d3dd60d391bbad87`.
Local artifacts are under `athena-pilot-build/<release_id>/`. S3 artifacts are
under this bucket prefix:

```text
research-data/
├── raw/                         Existing immutable collection records
├── source_documents/            Existing pinned SEC index evidence
├── manifests/                   Existing collection run records
├── checkpoints/                 Existing collection progress
├── curated/sec_pilot/releases/<release_id>/
│   ├── tables/
│   │   ├── companies/part-00000.parquet
│   │   ├── company_sectors/part-00000.parquet
│   │   ├── sec_filings/part-00000.parquet
│   │   ├── sec_filing_versions/part-00000.parquet
│   │   ├── sec_filing_companies/part-00000.parquet
│   │   └── sec_observations/part-00000.parquet
│   ├── release.json
│   ├── tables.sql
│   ├── queries.sql
│   └── verifications/            Successful Athena query results and IDs
└── athena-results/sec-pilot/     Athena query output
```

Each Athena table points at exactly one table folder in this release. There
is no crawler over the raw bucket. One compressed Parquet file per table is
appropriate for this tiny example; date partitioning and file compaction
belong in the larger incremental pipeline, not thousands of tiny company
partitions. Athena table metadata resides in Glue, while the records remain
in S3. [AWS table documentation](https://docs.aws.amazon.com/athena/latest/ug/creating-tables.html).

## Tables and expected results

| Table | Rows | Meaning |
|---|---:|---|
| `companies` | 20 | Provisional company universe, including companies with no filings that day |
| `company_sectors` | 20 | Sector assertions with review status, evidence and validity dates |
| `sec_filings` | 11 | Latest observed state per accession within the selected input runs |
| `sec_filing_versions` | 11 | Distinct observed content/metadata versions; revisions are retained |
| `sec_filing_companies` | 11 | Company links for the latest filing state, explicitly marked candidate or confirmed |
| `sec_observations` | 22 | Individual collection observations and their raw-file/manifests/source lineage |

`record_id` is the stable filing join key. `version_id` identifies a distinct
semantic version; `observation_id` identifies an individual collection
observation. Repeated daily/historical collection does not create additional
filings in `sec_filings`. A changed payload, match, or availability metadata
creates a new version. Latest selection uses ingestion time and then
observation ID as a deterministic tie-breaker; this is latest *observed*
state, not a claim about the provider's revision order.

All 11 real pilot company links are **candidate** matches. Nothing in curation
promotes a provisional name match into a verified legal entity. Sector counts
include these candidates and current configured sector assertions:
biotech 5, robotics 3, energy storage 2, semiconductors 1. Sector memberships
may overlap in larger datasets; use distinct filing IDs when aggregating.

`filing_date` is a Parquet/Athena date. Offset-bearing observation and
availability values remain ISO 8601 strings to retain their precision;
`from_iso8601_timestamp` can parse observation times in queries. The 11
`available_at` values remain null. Ingestion time and filing date do not
establish when a version became publicly available. Current provisional
company/sector information also cannot establish historical classification.
This release must not be treated as point-in-time HMM/TFT features.

## Try these queries

Inspect the deduplicated filings:

```sql
SELECT accession_number, form, filing_date, observation_count,
       version_count, entity_match_status, available_at
FROM optima_sec_pilot.sec_filings
ORDER BY accession_number;
```

Inspect the company matches:

```sql
SELECT c.canonical_name, f.accession_number, f.form, f.filing_date,
       l.match_status, l.match_basis
FROM optima_sec_pilot.sec_filings f
JOIN optima_sec_pilot.sec_filing_companies l ON f.record_id = l.record_id
JOIN optima_sec_pilot.companies c ON l.company_id = c.company_id
ORDER BY c.canonical_name, f.accession_number;
```

Count filings by configured sector, including candidate matches:

```sql
SELECT s.sector_id, count(DISTINCT l.record_id) AS filings
FROM optima_sec_pilot.sec_filing_companies l
JOIN optima_sec_pilot.company_sectors s ON l.company_id = s.company_id
WHERE s.review_status <> 'rejected'
GROUP BY s.sector_id
ORDER BY s.sector_id;
```

Trace a filing back to its observations and raw evidence:

```sql
SELECT f.accession_number, o.observation_id, o.run_id, o.ingested_at,
       o.source_manifest_keys, o.raw_batch_keys, o.source_snapshot_keys
FROM optima_sec_pilot.sec_filings f
JOIN optima_sec_pilot.sec_observations o ON f.record_id = o.record_id
ORDER BY f.accession_number, o.ingested_at;
```

Lineage keys are relative to `s3://data-collection-059416028963-us-east-1-an/research-data/`.
The release's `queries.sql` includes automated row counts, sector counts,
match status checks, unknown-availability checks and a preview query.

## Reproduce and publish

Use Python 3.12 and the isolated `.venv-athena` environment. Dependencies are
listed in `requirements-athena.txt`. `config/sec-athena-pilot.json` explicitly
selects the two source manifests; no additional SEC requests are made.

```bash
.venv-athena/bin/python -B sec_athena_pilot.py prepare
# Use the release directory printed by prepare for both commands:
.venv-athena/bin/python -B sec_athena_pilot.py publish --release-dir athena-pilot-build/RELEASE_ID
.venv-athena/bin/python -B sec_athena_pilot.py deploy --release-dir athena-pilot-build/RELEASE_ID
```

Preparation checks complete/exhausted status, committed manifest history,
configuration and raw-batch hashes, row counts, record schemas, pinned source
hashes, and presence of every issuer row in the original index. Failed,
partial, orphaned, or corrupt inputs are rejected. Separate Parquet schemas
give null columns explicit types. Each local file is read back before release.

Publication uses conditional writes, verifies uploaded bytes, and writes the
release marker last. Table registration happens only after publication.
The release ID includes input manifest hashes, curator/schema version,
configuration and Parquet library version. Rerunning the same release is
safe. Existing unrelated databases/workgroups or tables pointing at a
different release are rejected rather than overwritten.

Deployment creates a dedicated workgroup using Athena engine 3, encrypted
query results and a 100 MiB per-query scan limit. It compares live SQL results
to the prepared release expectations and saves query IDs and scan statistics.
An incomplete deployment can be retried using the same release directory.
No scheduling, IAM policy changes, or raw-data deletion is performed.

The EC2 role originally had S3 access only. The operator subsequently granted
Athena and Glue access. `config/sec-athena-pilot-policy.json` is an optional
scoped policy for these additional services; it assumes the existing S3 access.

This is a bounded in-memory pilot and an immutable release, not a scheduled
incremental service. New collection runs do not silently change these tables.
Before expanding, review identity mappings, revisions, availability semantics,
and queries. Incremental publication, release switching, larger-scale date
partitions, and the remaining collectors are the next implementation work.

## Validation

```bash
.venv-athena/bin/python -B -m unittest \
  test_research_contract test_collection_storage test_sec_filings test_sec_athena_pilot
```

The 84 offline tests passed, including curation regressions for revisions,
candidate links, cofilers, rejected sectors, corrupt inputs, uncommitted runs,
Parquet date types, idempotent publication, and local artifact tampering.
Live Athena evidence is saved in the release's `verifications/` folder after
all query comparisons pass.

The successful table-count query is
`bbe34750-2e71-48f4-85aa-9109f5806987`; the company/filing preview is
`2a36307c-7238-4b82-92db-812f834e0a98`. They are also visible in the workgroup's
recent query history. The five queries scanned 9,109 bytes in total according
to Athena execution statistics (this is scan volume, not billed usage).
