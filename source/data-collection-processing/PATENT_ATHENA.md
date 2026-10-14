# Patent research in Athena

Region: `us-east-1`. Data source: `AwsDataCatalog`.
Database: `optima_patent_research`.
Workgroup: `optima-patent-research` (100 MiB scan limit per query).

The January 2015 historical backfill is also live in four separate monthly views.
See [PATENT_BACKFILL_ATHENA.md](PATENT_BACKFILL_ATHENA.md) for queries, coverage
and the repeatable monthly publication process. The pilot below is preserved.

Live publication verified September 23, 2026: eight release-validation queries
and two additional coverage/application-join checks passed. Relevant local
regression suite: 49 tests passed, including ten new Athena-curation tests.

The first release contains the reviewed global January 2025 publication sample,
current registry evidence and two bounded US assignment-history cohorts. It is
not a complete historical backfill, a current global daily feed, or a model-ready
ownership dataset. A publication's authority is not the assignee's domicile.

Release ID:
`0aebe0d989788fc9a9913b4a3f5edde818aca1a75f6b5c7b6c99c0c03a65b3cb`.

S3 release:
`s3://data-collection-059416028963-us-east-1-an/research-data/curated/patents/releases/0aebe0d989788fc9a9913b4a3f5edde818aca1a75f6b5c7b6c99c0c03a65b3cb/`.

The local `patent-athena-build/<release>/athena-verification.json` and S3
`verifications/` artifacts record actual query IDs, scan bytes and results.
Only a verification artifact with `status: verified` establishes successful
publication and SQL checks. The immutable preparation report remains
`locally_validated`; older review reports retain their original publication status.

## Tables and expected contents

| Table | Rows | Meaning |
| --- | ---: | --- |
| `patent_publications` | 78,542 | One reviewed observation per publication in this release |
| `patent_sector_reviews` | 77,876 | Supported and pending technology/category decisions |
| `patent_party_links` | 74,859 | Reported assignee/applicant names, candidate IDs and reviewed links |
| `patent_entity_reviews` | 20 | High-volume names and full registry alternatives/evidence |
| `patent_company_reconciliation` | 5 | Selected registry entities and shared-universe reconciliation status |
| `patent_listing_reviews` | 7 | Four supported depositary-receipt relationships and three pending listings |
| `patent_assignment_histories` | 23 | Verified current USPTO application-history responses |
| `patent_assignment_events` | 29 | Recorded events; ties and multiple recipients retained |
| `patent_coverage` | 1 | Cohort scope, review versions, coverage counts and limitations |

The publication window is January 1–31, 2025, including 31,216 CN publications.
54,370 publications have at least one supported technology sector, and 3,459 have
at least one supported company-name link. Sector counts overlap: biotech 16,046;
energy storage 15,597; robotics 2,820; semiconductors 20,102.

`patent_publications` contains reviewed publication metadata, titles, sector/name
decisions and source-evidence references. Full provider payloads remain in the
original audited S3 collection; filing dates, priority dates and family details
are not yet flattened into this review-focused table.

## Check manually

Open the Athena query editor in `us-east-1`, choose workgroup
`optima-patent-research`, data source `AwsDataCatalog`, and database
`optima_patent_research`. Run:

```sql
SELECT publications, supported_technology_publications,
       supported_name_publications, assignment_applications,
       publication_start, publication_end,
       current_ownership_verified_records, coverage_note
FROM optima_patent_research.patent_coverage;
```

Expected leading counts: `78542`, `54370`, `3459`, `23`. Verified current
ownership remains `0`.

Supported sectors only, with publications deduplicated within each sector:

```sql
SELECT sector_id, count(DISTINCT observation_id) AS publications
FROM optima_patent_research.patent_sector_reviews
WHERE review_status = 'supported'
GROUP BY sector_id
ORDER BY sector_id;
```

Browse Chinese publications in any of the four supported sectors:

```sql
SELECT publication_number, publication_date, title,
       supported_sector_ids, reported_company_names,
       has_supported_name_link, current_ownership_status
FROM optima_patent_research.patent_publications
WHERE publication_authority = 'CN'
  AND cardinality(supported_sector_ids) > 0
ORDER BY publication_date, publication_number
LIMIT 50;
```

Find supported Applied Materials name links using its registry identity:

```sql
SELECT DISTINCT p.publication_number, p.publication_date, p.title,
       l.reported_name, l.review_status, l.company_id,
       l.registry_entity_id, p.current_ownership_status
FROM optima_patent_research.patent_publications p
JOIN optima_patent_research.patent_party_links l
  ON p.observation_id = l.observation_id
WHERE l.registry_entity_id = 'lei:41BNNE1AFPNAZELZ6K07'
  AND l.review_status = 'registry_name_supported'
ORDER BY p.publication_date, p.publication_number
LIMIT 50;
```

View the reviewed listing corrections and historical trading intervals:

```sql
SELECT exchange_mic, ticker, original_security_type, reviewed_security_type,
       relationship_type, depositary_issuer_name, registry_entity_id,
       listed_from, trading_from, valid_to_exclusive, review_status, source_url
FROM optima_patent_research.patent_listing_reviews
ORDER BY exchange_mic, ticker;
```

Join US publications to collected assignment histories by application identity,
without multiplying publications by the number of assignment events:

```sql
SELECT p.publication_number, p.title, h.application_number,
       h.assignment_event_count, h.comparison_status, h.current_ownership_status
FROM optima_patent_research.patent_publications p
JOIN optima_patent_research.patent_assignment_histories h
  ON regexp_extract(p.application_number, '^US-[0-9]{4}([0-9]{8})-A$', 1)
     = h.application_number
WHERE p.publication_authority = 'US'
ORDER BY p.publication_number;
```

For event details, query `patent_assignment_events` by application number. A
missing history row means the application is outside the 23-application cohort;
it does not mean no assignments exist. Within the 15-application registry
comparison cohort, 14 recipient names match and one response has no assignment
events. The earlier eight histories retain the original events and are marked
`outside_registry_comparison_cohort` rather than assigned a new comparison result.

## Company and listing reconciliation

The immutable patent release captures universe 0.2 and its then-current review
decisions. Universe 0.3 now incorporates LG Energy Solution, Applied Materials,
Samsung Display and LG Display with stable registry-backed IDs; display-sector
membership remains pending. Four receipt-derived placeholders are disabled,
and the receipt listings identify Applied Materials as their underlying issuer.
See `COMPANY_UNIVERSE.md`. The patent release's captured fields are not rewritten.
For current registry-to-company joins, join `registry_entity_id` (remove `lei:`)
to `optima_eodhd_research.universe_identifiers` where `system='lei'` and
`review_status='verified'`; preserve both snapshots' versions in derived results.

Four reviewed listing relationships identify Applied Materials as the underlying
issuer of a depositary receipt. The receipt issuers remain separate:

- `AMAT.NEO`: CIBC Canadian depositary receipt; traded from February 4, 2025,
  delisted at the close on December 22, 2025. The exclusive end is December 23.
- `AMAT.TO`: CIBC Canadian depositary receipt; listed/traded from December 23, 2025.
- `AMAT01.BK`: Bualuang depositary receipt; listed June 17, trading June 18, 2026.
- `AMAT23.BK`: InnovestX depositary receipt; listed June 11, trading June 12, 2026.

Sources: [TSX exchange bulletin](https://www.tsx.com/en/news/new-company-listings?id=2238),
[SET AMAT01 listing notice](https://www.set.or.th/en/market/news-and-alert/newsdetails?id=105125500),
[SET AMAT23 listing notice](https://www.set.or.th/en/market/news-and-alert/newsdetails?id=105065400).
Exact HTML responses, URLs, timestamps and hashes are saved under the release's
`artifacts/listing-evidence/` directory. The reviewed rules are in
`config/patent-listing-review.v1.json`. This patent release preserves the original
listing snapshot alongside the corrections; the later shared universe 0.3 now
incorporates the four supported receipt relationships.

These are underlying-security relationships, not evidence that a depositary
institution owns the underlying company's patents. Historical dates supplied by
the exchange also do not establish historical data availability for the models.

## Reproduce, publish and verify

```bash
.venv-athena/bin/python patent_athena.py prepare
.venv-athena/bin/python patent_athena.py publish --release-dir patent-athena-build/RELEASE_ID
.venv-athena/bin/python patent_athena.py deploy --release-dir patent-athena-build/RELEASE_ID
```

Preparation checks the exact published review artifacts against their S3 hashes,
revalidates their committed input-manifest/configuration anchors, and fully
revalidates the small assignment cohorts and raw source hashes. The original
review stage performed the full raw publication/source-evidence audit. Release
IDs include input versions, schemas, evidence hashes and destination settings.
All nine Parquet tables undergo local schema round-trip checks, S3 read-back
verification, and Athena count/date/sector/referential-integrity queries.

The first deployment uses a dedicated database and workgroup. Rerunning the same
release is idempotent; advancing existing owned tables requires the explicit
`--update-existing` option. Table updates are sequential, so future recurring
publication needs an atomic release-selection design before automation. The
current release is manually published; no new patent timer is enabled.

Next work: expand assignment/legal-status sources beyond the
bounded US cohorts; complete historical/daily collection coverage and automate
incremental Athena publication. Model eligibility remains false until historical
availability and entity/feature timing are established.
