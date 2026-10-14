# Evidence-based patent review

Current publication: nine patent tables are live and verified in
`optima_patent_research` as of September 23, 2026. See `PATENT_ATHENA.md` for
manual queries, reviewed listing corrections, and exact coverage. Review
release artifacts below remain immutable; their original `not_published` status
describes that review stage, not the later Athena publication.

`patent_adjudication.py` replaces a single blanket pending flag with independent
decisions for invention technology, reported company links, historical identity,
and current ownership. It reads only committed complete collection manifests
and verifies raw records, universe snapshots and source-response hashes before
creating a versioned review release. Original observations are preserved.

## What is supported automatically

Technology decisions use the full source CPC symbol, preserving the slash and
group boundaries. The reviewed mappings and authoritative definitions are in
`config/patent-review-policy.v1.json`. Specific classifications can support one
or more of the four target sectors. Mechanical and hydrogen storage now have
specific CPC support as well as their older keyword discovery rules.

Broad discovery matches remain useful for recall, but do not become supported
decisions by themselves. Examples include general G05D vehicle guidance, manual
B25J manipulators, fuel-cell electrodes in H01M4, generic deposition, and the word
"electrode". Unsupported does not mean rejected: these records need more specific
codes or document evidence. Source CPC classification is itself evidence, not a
claim that the invention has been independently assessed in full.

Company links require an exact normalized legal name (Unicode, punctuation and
case normalization; legal suffixes are retained), a unique registry-verified
legal entity, and a verified LEI or CIK in the versioned universe. Verified
aliases can be used only when explicit validity dates cover the publication.
Pending aliases cannot establish a supported link. A unique verified legal
entity can support a reported-party name link while unresolved listing entities
remain in the candidate list; those listing entities are not merged.

The resulting status is `registry_name_supported`, not verified current patent
ownership. The link identifies the company name reported by the source; it does
not prove the company's identity at a historical date or a complete chain of
title. Company-sector memberships retain their own evidence and review dates.
They are not substituted for the patent's technology classifications.

## First complete review

Reviewed input: January 2025 global publication sample, 78,542 observations,
including 31,216 CN publications. Collection manifest:
`manifests/collection_runs/source=google_patents_bigquery/dataset=patent_records/run_a72df734-9944-4036-aa68-9452c35c60c4/final.json`.

Release: `f5f54302dccbf2a29cf1c70fe4a6df9169f06be93cda55a104b01d3b7d1cc133`.

- 54,370 publications have at least one supported technology sector.
- 599 publications have registry-supported reported-party name links.
- Sector counts overlap: biotech 16,046; robotics 2,820; semiconductors 20,102;
  energy storage 15,597.
- Storage categories overlap: batteries 14,889; supercapacitors 455; thermal 374;
  mechanical 70; hydrogen 114.
- 24,812 records still need review for at least one proposed technology category;
  some already have support for another category.
- 13,709 records have no reported assignee/applicant in the exported fields.
- 957 records have competing company candidates; 2,263 have unverified company
  identities or aliases; 61,563 have at least one assignee outside the universe.
  These conditions overlap.
- The company queue groups work by reported name and role (24,210 groups),
  sorted by the number of affected records. This avoids reviewing the same
  assignee separately for every publication.

High-volume unresolved names include Samsung Electronics, LG Energy Solution,
Taiwan Semiconductor Manufacturing, Samsung Display and BOE. Applied Materials
maps to five unresolved listing-derived entities and requires identifier-based
reconciliation. No automatic subsidiary-to-parent consolidation is applied.

S3 release prefix:
`s3://data-collection-059416028963-us-east-1-an/research-data/curated/patent_review/f5f54302dccbf2a29cf1c70fe4a6df9169f06be93cda55a104b01d3b7d1cc133/`

Files: `decisions.jsonl`, `company-review-queue.jsonl`, `policy.json`, `review.json`.
These review artifacts now feed the separate Athena release. All original
point-in-time availability limitations remain. No current ownership or historical
model-feature eligibility is asserted by this release.

## Assignment history

`patent_assignments.py` collects the official USPTO application response and
retains recorded assignment history, execution/recordation dates, recipients,
assignors and document references. It distinguishes assignments, security
interests, releases, mergers and name changes. Missing dates stay unknown.
Multiple assignments on the latest recorded date remain multiple events.

```bash
.venv-athena/bin/python patent_assignments.py \
  --applications 18715784 18220162 18739089 18909005 \
                 18915271 18900035 18680477 18784595 \
  --observed-day 2026-09-22 --max-records 8
```

The observed day denotes when the current history is collected, not a claim
that the response recreates a historical snapshot. Each event retains its
source-provided dates. Partial cohorts resume from the last committed application.
Completed cohorts are skipped; use a new observed day for a later observation.

The eight-application validation cohort is complete, manifest
`manifests/collection_runs/source=uspto_odp/dataset=patent_assignment_records/run_2a6246d1-6e9d-4797-9877-77d9a359647b/final.json`.
These history records are separate from the global review release and must be
joined by application identity in curation. They do not establish a full chain
or current legal title. USPTO itself distinguishes recordation from a title
determination: https://www.uspto.gov/web/offices/pac/mpep/s301.html.

All eight responses and their evidence hashes were verified. They contain 15
recorded assignment events. `reports/patent-assignment-review-2026-09-22.json`
shows the source facts. For application 18900035, the publication export names
Annovis Bio, while the latest recorded assignment recipient in the fetched
history is the Trustees of Columbia University. Application 18715784 has six
same-date recorded assignment events naming several BASF entities. These are
review triggers, not a conclusion about current title or the legal effect of
the transactions. A license or corporate relationship also requires its own
evidence; it is not inferred from the difference in names.

## Repeat the review

```bash
.venv-athena/bin/python patent_adjudication.py \
  --manifest manifests/collection_runs/source=google_patents_bigquery/dataset=patent_records/run_a72df734-9944-4036-aa68-9452c35c60c4/final.json \
  --publish
```

The next company-resolution work is to corroborate high-volume assignee legal
entities, distinguish them from listings and subsidiaries, and add supported
aliases to a new universe release. China and other jurisdictions also need
source-specific assignment/legal-status evidence for current-ownership queries.
The global table currently lags to March/April 2026, so it cannot resolve current
ownership or daily global freshness on its own.

## High-volume entity review: 2026-09-23

`patent_entity_review.py` adds a separately versioned GLEIF crosswalk for the
20 highest-volume unresolved names. It verifies the parent review file hashes,
retains complete registry responses with their URLs, collection timestamps and
SHA-256 hashes, and joins decisions by observation ID. The cohort touches 8,999
distinct publications. It supports five additional reported-name links covering
2,860 publications:

| Reported entity | Publications | LEI |
| --- | ---: | --- |
| LG Energy Solution | 960 | 988400QX6P286XA6ZS85 |
| Samsung Display | 800 | 9884004ARY4RODDUCT12 |
| Applied Materials | 617 | 41BNNE1AFPNAZELZ6K07 |
| Intel | 252 | KNX4USFCNGPY45LOCE31 |
| LG Display | 231 | 988400P37K91W0SABO95 |

Release: `19b5e77645eec2c15f7d3f4b5639c4d42c351cbd8c18fb382992998d0122b8b0`.
Published S3 prefix:
`s3://data-collection-059416028963-us-east-1-an/research-data/curated/patent_entity_review/19b5e77645eec2c15f7d3f4b5639c4d42c351cbd8c18fb382992998d0122b8b0/`.

Files include `entities.jsonl`, `publication-links.jsonl`, `assignment-cohort.json`,
`fetch.json`, `review.json`, and original registry responses under `evidence/`.
A readable local summary is `reports/patent-entity-review-2026-09-23.csv`.

The matching policy retains substantive words and legal forms. It expands only
terminal co/company, ltd/limited, corp/corporation and inc/incorporated tokens;
it does not expand MFG, IP MAN or other substantive abbreviations. Current
registry legal names and explicit alternative-language/transliterated legal
names are eligible. Previous names, unbounded search results, competing LEIs,
inactive entities, lapsed registrations, and less-than-full corroboration do
not establish a supported current registry-name link. This is a conservative
research policy, not a claim that a lapsed LEI invalidates a company's identity.

Remaining cohort statuses: one ambiguous name, five needing registry-status or
name review, and nine without an exact registry-name match. Absence from these
English-name searches does not mean the legal entity does not exist. Samsung
Electronics has two matching LEIs with different registration records, so neither
is chosen automatically. CATL's Hong Kong entity is kept separate from the
mainland company and other group entities. Chinese local-language registry
evidence and patent-document addresses remain necessary for several cases.

The crosswalk uses stable `lei:<identifier>` entity references. Intel's LEI
already maps to a verified company ID. Applied Materials' five listing-derived
company candidates remain intact: they lack company-level identifiers and cannot
be merged based on this name match. Shared universe 0.2, existing listing IDs,
historical aliases and sector memberships have not been changed. These name
links do not establish historical identity, current title or model eligibility.

```bash
.venv-athena/bin/python patent_entity_review.py fetch \
  --review-root patent-review-build/f5f54302dccbf2a29cf1c70fe4a6df9169f06be93cda55a104b01d3b7d1cc133 \
  --evidence-root reports/patent-entity-evidence-2026-09-23 --limit 20
.venv-athena/bin/python patent_entity_review.py build \
  --review-root patent-review-build/f5f54302dccbf2a29cf1c70fe4a6df9169f06be93cda55a104b01d3b7d1cc133 \
  --evidence-root reports/patent-entity-evidence-2026-09-23
```

Fetch resumes completed queries after verifying their evidence hashes. Reuse the
same evidence directory for the same cohort; choose a new directory for a new
observation or expanded cohort. Searches are bounded at 200 registry results;
truncation remains explicit and prevents unique-match decisions.

## Expanded US assignment comparison: 2026-09-23

The entity release selects three distinct US applications per supported entity
(15 total) from the original publication review. Selection deduplicates
application numbers and retains the source publication and reported names.

```bash
.venv-athena/bin/python patent_assignments.py \
  --cohort-file patent-entity-build/19b5e77645eec2c15f7d3f4b5639c4d42c351cbd8c18fb382992998d0122b8b0/assignment-cohort.json \
  --observed-day 2026-09-23 --max-records 15 \
  --output reports/patent-assignment-cohort-2026-09-23.json
```

All 15 official responses are collected and their evidence hashes verified.
Complete manifest:
`manifests/collection_runs/source=uspto_odp/dataset=patent_assignment_records/run_65d78ea3-aa1c-4702-86ae-a538e93f486e/final.json`.

`patent_assignment_review.py` joins the committed responses to the exact reviewed
cohort by application number, requires matching universe hashes, and rejects
missing, extra, or duplicate application observations. Fourteen histories each
contain one recorded assignment whose recipient name matches the corresponding
registry entity. Samsung Display application 18755986 contains no assignment
events in the returned response; this does not prove an absence of ownership.
All 15 current-ownership decisions remain `not_established`.

Comparison release:
`82d08ced86df0c95952978d111e813ebc4dc77e4daaaf99c138cd847016cc735`.
Published S3 prefix:
`s3://data-collection-059416028963-us-east-1-an/research-data/curated/patent_assignment_review/82d08ced86df0c95952978d111e813ebc4dc77e4daaaf99c138cd847016cc735/`.

This is a bounded validation cohort, not assignment coverage for all 2,860
publications or for non-US patents. Together with the first eight applications,
23 applications have now been collected, with 29 recorded events. Athena
publication is now complete (see `PATENT_ATHENA.md`); shared-universe
reconciliation and broader jurisdictional coverage remain. Regression validation
for this review stage: 52 tests passed.
