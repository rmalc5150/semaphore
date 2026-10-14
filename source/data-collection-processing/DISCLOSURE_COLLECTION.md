# Corporate disclosure migration

New `historical START END` and `daily [DATE]` paths are implemented for
`hkex_filings.py`, `company_press_releases.py`, `licensing_agreements.py`,
`ma_announcements.py`, and `strategic_transactions.py`. END is exclusive.
SEC index collection continues to use the previously migrated `sec_filings.py`.
`disclosure_collection.py documents` adds the document-text prerequisite.

The new paths write to the shared storage configuration and immutable run
layout. The legacy `day`/`month` commands retain their old behavior. The
coordinated runners now invoke shared paths; see COLLECTION_OPERATIONS.md.
Google News discovery in the old strategic
transaction path is still biotech-specific; its migration belongs to the
news group. The new strategic-transaction path operates on completed
disclosure documents and has no biotech-only gate.

## Company and sector coverage

The configured sectors are biotech, robotics, semiconductors, and energy
storage, including batteries, supercapacitors, thermal, mechanical and
hydrogen-based storage. A company may belong to multiple sectors.

**Shared collectors now use reviewed universe 0.2.0.** The completed EODHD inventory contains
141,783 active/delisted listings across 66 selected provider exchange codes.
The expanded Athena release contains 9,438 profile symbols and explicit sector,
identity, listing and private-discovery tables. Versioned universe 0.2.0 exists,
although profile coverage and legal-identity reconciliation remain partial.
See `EODHD_ATHENA.md` and `COMPANY_UNIVERSE.md`. Previously published pilots
still contain the 20-company snapshot. Neither the old seed nor the partial
reviewed universe represents all companies in the designated sectors.

`--selection all` retains raw discovery records, including unmatched companies.
`--selection universe` restricts records to confirmed or candidate matches in
the supplied universe; repeatable `--sector` narrows those memberships. Rejected
or disabled companies do not qualify. Neither mode promotes name matches to
verified legal identities. HKEX short names can fail to match legal names;
cross-listing and provider-identifier reconciliation remain important work.

SEC and HKEX provide regional listed-company coverage, not a complete global
or private-company inventory. All sector filters use the captured universe
version; they do not establish historical membership.

## Collection and dependencies

HKEX uses the public JSON endpoint invoked by the official search page:
`https://www1.hkexnews.hk/search/titleSearchServlet.do`.
Its public client script is
`https://www1.hkexnews.hk/ncms/js/titlesearch_research.js`.
Pagination expands `rowRange`; it is not an independent numbered page.
The collector checks total/loaded counts, completion flags, unique NEWS_IDs,
source dates, document hosts, and the entire previously observed row prefix.
Unchanged/repeated results before exhaustion produce a partial result.
Historical ranges are traversed one source-calendar day at a time. API response
bytes and per-page identity/cursor receipts are saved. NEWS_ID is the provider
identity; stock codes are preserved as source metadata, not fabricated entity IDs.
`--hkex-stock-id` is the provider search ID, not the exchange ticker.

HKEX release times retain Asia/Hong_Kong offsets. Filing/release dates remain
source-calendar dates. `available_at` stays unknown; retrieving a document now
does not prove that its current version existed at an earlier model cutoff.

Derived stages require explicit `--source-manifest` arguments. They reject
partial, failed, uncommitted, corrupt, wrong-source, mixed-configuration and
date-gap prerequisites before generating output. The requested source set is
part of the task scope. Document collection defaults to both SEC and HKEX;
an explicit `--require-source sec_edgar` makes a bounded SEC-only scope.
Every output preserves its parent record, observation, batch and manifest.
Resume advances one input document at a time, including zero-candidate inputs.
Input manifest hashes pin the inputs; selecting newer inputs creates a new task.
Consequently derived watermarks are scoped to those pinned prerequisites, not
a global scheduler's catch-up cursor.

Document collection fetches SEC complete submissions and eligible textual
exhibits, or HKEX PDF/HTML. SEC accession identity is checked. The default
SEC form scope is 8-K, 6-K, 10-K, 10-Q and their amendments, S-4/S-4/A, 425,
and DEFM14A; `--sec-form` overrides it explicitly. It is recorded in scope.
Binary exhibits, unreadable or encrypted PDFs, and PDF pages without extracted
text stop the attempt instead of becoming successful empty documents. OCR and
review of those cases remain future work. Source responses are limited to
64 MiB by the shared evidence client. Requests use the supplied Optima Holdings
SEC contact identity and bounded pacing/retry.

PR, licensing, M&A and strategic-transaction records are **unreviewed
candidates**. Matched terms and excerpts are retained. Filing-form matches
alone are also labeled as candidates. A term can describe a historical,
negated, proposed or unrelated event. No extracted amount, completion status,
party relationship or product identity is promoted to a confirmed fact.
The first three classifiers include selected Chinese terms; strategic
transaction patterns currently use English. This is not full multilingual
classification coverage.

```bash
# Source collection and an intentional partial/resume test.
.venv-athena/bin/python hkex_filings.py historical 2024-06-02 2024-06-03 \
  --page-size 10 --max-pages 1
.venv-athena/bin/python hkex_filings.py historical 2024-06-02 2024-06-03 \
  --page-size 10

# Fetch documents from a committed SEC manifest, in an explicit SEC-only scope.
.venv-athena/bin/python disclosure_collection.py documents historical 2024-06-03 2024-06-04 \
  --source-manifest MANIFEST_KEY --require-source sec_edgar

# Derive candidates from completed document collection.
.venv-athena/bin/python licensing_agreements.py historical 2024-06-03 2024-06-04 \
  --source-manifest DOCUMENT_MANIFEST_KEY

# Daily mode; its prerequisites must cover the requested source-calendar day.
.venv-athena/bin/python company_press_releases.py daily 2024-06-03 \
  --source-manifest DOCUMENT_MANIFEST_KEY
```

`--max-records` caps a derived attempt and yields partial before exhaustion.
Repeat identical arguments to resume after the earlier worker has stopped.
`--refresh` deliberately recollects. No recurring jobs have been installed.

## Bounded live Athena pilot

Configuration: `config/disclosure-athena-pilot.json`.
Release: `f583b8bc26b83c42fab493e3b6825fcb2f65dbeeed6269d1b225558fcd24ec86`.
Database: `optima_disclosures_pilot`; workgroup: `optima-disclosures-pilot`;
region: us-east-1; data source: AwsDataCatalog.

| Table | Expected records | Scope |
|---|---:|---|
| disclosures | 28 | HKEX metadata for June 2, 2024; all discovery records |
| documents | 2 | Eligible corporate forms from the completed June 3 SEC pilot |
| event_candidates | 6 | Two PR, one licensing, one M&A, two strategic candidates |
| companies | 20 | Existing provisional shared universe |
| company_sectors | 20 | Existing provisional sector assertions |

Category counts overlap: six candidate records are derived from two documents,
not six verified transactions. HKEX document extraction is implemented but the
published document/candidate cohort here is SEC-only. This is a set of different
bounded source/date scopes, not a synchronized global snapshot.

```sql
SELECT dataset, count(*) AS candidates
FROM optima_disclosures_pilot.event_candidates
GROUP BY dataset
ORDER BY dataset;

SELECT origin_source, dataset, event_date, title, data_json
FROM optima_disclosures_pilot.event_candidates
ORDER BY dataset, provider_id;
```

The curator reads explicit complete manifests, checks raw/evidence checksums,
selects the latest observation per logical record within those inputs, and
validates typed Parquet round trips. Raw history remains immutable; this pilot
does not add an all-versions table. Raw manifest and batch references remain in
each curated row. Publication uses immutable S3 prefixes; deployment rejects
conflicting table locations. Confirm live deployment using the release's
`athena-verification.json` and its `status: verified`; local preparation alone
does not establish Athena publication.

```bash
.venv-athena/bin/python disclosure_athena.py prepare
.venv-athena/bin/python disclosure_athena.py publish --release-dir disclosure-athena-build/RELEASE_ID
.venv-athena/bin/python disclosure_athena.py deploy --release-dir disclosure-athena-build/RELEASE_ID
```

The 154 relevant tests passed, including source pagination/resume, all four
sector memberships, failed prerequisites, source/date gaps, corrupted evidence,
document lineage, SEC identity/exhibit extraction, EODHD credential handling,
and Parquet round trips. The HKEX live pilot resumed an intentional one-page
partial run to all 28 records. Both SEC documents and all four derived runs
completed in S3. Athena deployment subsequently passed all four verification
queries. The table-count query ID is
`e6302e33-0cef-45da-bd16-908410de5c76`; the local release's
`athena-verification.json` has `status: verified`, and its immutable verification
record is also stored beside the S3 release.
