# Research data contract — step 1

Status: the local contract, validation universe, and examples are implemented.
The shared local/S3 writer and run/checkpoint storage are now implemented in
step 2; see `COLLECTION_STORAGE.md`. Step 3's SEC collector has completed a
bounded live S3 pilot; see `SEC_COLLECTION.md`. Other collector migrations
remain later steps. A bounded SEC Athena pilot is published and verified;
see `SEC_ATHENA_PILOT.md`. Legacy collector output paths are preserved.

## Scope and files

Coverage is global and includes private companies. Companies may belong to
multiple sectors: `biotech`, `robotics`, `semiconductors`, and `energy_storage`.
Storage includes batteries, supercapacitors, thermal, mechanical, and
hydrogen-based storage. This does not imply automatic inclusion of every
generation business or every hydrogen business; the activity must involve
storage. Medical sources remain applicable to biotech and relevant medical
applications, while general sources can cover all sectors.

| File | Purpose |
|---|---|
| `config/company-universe.v0.1.json` | Version 0.1.0 validation universe; 20 imported pilot entries |
| `config/sectors.v1.json` | Version 1.0.0 sector and subsector taxonomy |
| `schemas/research-data.schema.json` | Draft 7 JSON Schema, including all entity definitions |
| `research_contract.py` | Identity helpers and cross-record validation |
| `validate_research_data.py` | Read-only local validation command |
| `examples/research-contract/universe.json` | Entirely fictional entity and relationship examples |
| `examples/research-contract/records.jsonl` | Original, revised, and unmatched/availability-unknown observations |
| `test_research_contract.py` | Offline checks for historical data and identity errors |

The pilot is a discovery seed, not a comprehensive global company list or a
verified historical universe. Names, aliases, and sector labels were imported
from `patent_pilot_companies.json`, without introducing unverified listing,
ownership, domicile, product, or personnel facts. Every imported company and
alias is marked `pending`; organization type is `unresolved_organization`.
`collection_enabled=true` permits future discovery requests, not automatic
entity matching or use in historical model features. Some source aliases may
identify separate subsidiaries or business units and must not be merged merely
because the old pilot grouped them together. Dates of observation record this
import, not the date the underlying facts first became public.

The legacy patent configuration remains in place for existing scripts. During
their later migration, the shared universe will replace those duplicated lists.
Changing this new configuration does not yet alter any collector's behavior.

## Identity and entity model

Entity IDs are lowercase UUID4 values with a readable prefix, generated once
and retained in all later universe versions. Never regenerate IDs from names,
tickers, aliases, dates, or array positions. A rename retains its ID. If a
provisional entry is discovered to conflate entities, create distinct IDs and
retain the old configuration version and correction evidence; do not silently
rewrite prior observations.

| Entity / assertion | ID / key | Meaning |
|---|---|---|
| Company | `cmp_<uuid>` | Organization, with explicit legal-entity/business-unit/unresolved type |
| Listing | `lst_<uuid>` | A security's listing on an exchange, including share class and security type |
| Product | `prd_<uuid>` | Product, development program, or identifiable technology |
| Person | `per_<uuid>` | Person independent of display name or employer |
| Company alias | `als_<uuid>` | Dated, evidenced name assertion linked to a company |
| External identifier | `xid_<uuid>` | Dated identifier from a named system, linked to an entity |
| Relationship | `rel_<uuid>` | Dated relationship between stable entities |
| Collection run | `run_<uuid>` | Run identifier reserved here; storage and lifecycle follow in step 2 |

Use an exchange MIC for listings. A ticker alone is never globally unique.
Keep ADRs, ordinary shares, and separate exchange listings distinct. External
identifiers can hold SEC CIKs, LEIs, source company IDs, or security identifiers.
Each source adapter must document normalization in its namespace (for example,
consistent CIK padding). Values are case-sensitive opaque strings; the contract
does not guess provider-specific normalization. Do not use names as source IDs
when a durable provider ID exists.

Companies contain sector membership assertions with optional subsector IDs,
classification basis, evidence, review status, and validity dates. Document
technology classification belongs to the dataset payload and is independent
of company sector membership. The taxonomy maps legacy `semiconductor` to
`semiconductors`, and `battery` to `energy_storage`; that mapping does not prove
the original companies cover the broader storage subsectors.

Company aliases can represent legal names, former names, trade names,
transliterations, or source names. Ambiguous shared aliases produce validation
warnings and must not be automatically resolved. Canonical names and public/
private status describe the observation in that universe version, not an
assertion that the same values applied for all earlier dates.

Relationship directions:

| Type | Subject → object |
|---|---|
| `subsidiary_of`, `business_unit_of` | Child company → parent company |
| `owns`, `develops`, `manufactures` | Company → product |
| `licenses_in` | Licensee company → product |
| `licenses_out` | Licensor company → product |
| `employed_by`, `board_member_of` | Person → company |

Licensing relationships do not by themselves identify the counterparty; keep
transaction terms and participants in transaction records. Parent-child
relationships preserve separate company identities after an acquisition.

## Dates, evidence, and historical meaning

Every entity/assertion carries `observed_at`, `review_status`, and nonempty
`evidence` entries (`source`, `reference`, `note`). Review status is `pending`,
`verified`, or `rejected`. Verified means the assertion was reviewed; it is not
proof that the record is suitable for a historical model cutoff.

Validity intervals are `[valid_from, valid_to)`: start inclusive, end exclusive.
Both use source calendar dates. A null start means unknown, not "always true".
A null end means no established end, not proof of perpetual applicability.
Validation conservatively treats unknown boundaries as possibly overlapping
when detecting identifier conflicts. This is a collision check only, not a
historical eligibility rule. Preserve finer-grained source evidence in the raw
record when a day-level entity interval is insufficient.

| Collected-record field | Meaning |
|---|---|
| `event_at` | When the underlying event occurred; can be a planned future event |
| `available_at` | When the information in this particular payload version became publicly available |
| `source_updated_at` | Revision time reported by the provider |
| `ingested_at` | Actual retrieval time, with a UTC offset |
| `availability_basis` | `unknown`, `source_publication`, `source_revision`, `archive_evidence`, or `provider_metadata` |
| `availability_evidence` | Evidence establishing availability of this version |

The first three temporal fields are null or structured values:

```json
{"value": "2024-06-03", "precision": "day", "source_timezone": null}
```

```json
{"value": "2024-06-04T09:30:00-04:00", "precision": "second", "source_timezone": "America/New_York"}
```

Date-only data stays date-only. Instant values require an explicit offset and
matching precision (`second`, `millisecond`, or `microsecond`). The optional
source timezone retains known source context; it does not replace the offset.
Never manufacture an availability time from an event date, filing date, or run
date. Unknown availability has `available_at=null`, basis `unknown`, and an
empty availability evidence list. Known availability requires evidence.

Later feature preparation must apply a documented conservative cutoff policy
for date-only availability and source timezone uncertainty. An old filing date
does not make a newly revised patent, trial, or company record available to an
old prediction. Today's engagement counters are today's observations, even if
the underlying post is old. Unknown availability can be analyzed, but must not
silently become historical features; either exclude it or explicitly use
ingestion time as a conservative operational observation bound without changing
the source availability field. Universe versions used for modeling also need
review of historical membership, delisted/acquired entities, and survivor bias.

## Collected records and revisions

Each JSONL line is one `collected_record` envelope containing the source payload
as an object. Entity ID arrays allow one source document to involve several
companies, listings, products, or people without duplicating the raw document.
`entity_match_status` is `matched`, `partial`, or `unresolved`; unmatched records
are retained with empty ID arrays. Listing references must also include their
company in `company_ids`. `universe_version` records which identity configuration
was used for matching. Source-specific schemas and normalization belong to the
collector migrations; provider data within `payload` is not rewritten by this
validator.

`source_record_id` is provider-issued where possible. A documented composite
identity may be used otherwise (basis `documented_composite`); it must exclude
mutable payload values and collection time. The SEC migration will use a
normalized accession identity rather than just CIK + date + form, which can
collide. Changed payloads retain the same logical record ID, with a different
observation ID. New provider records such as separately accessioned amendments
retain distinct source identities.

Identity algorithm, contract version 1:

1. Canonical JSON is UTF-8, sorted object keys, compact separators, Unicode kept
   as text, and non-finite numbers rejected. This is the Python helper's defined
   serialization, not RFC 8785; array order and numeric representation matter.
2. `record_id = "rec_" + SHA256(canonical(["record-v1", source, dataset, source_record_id]))`.
3. `payload_hash = "sha256:" + SHA256(canonical(payload))`.
4. `observation_id = "obs_" + SHA256(canonical(entire envelope excluding observation_id))`.

`seal_record()` implements the algorithm without modifying its input. Retrying
the exact same envelope preserves the observation ID. A new run, retrieval time,
payload, entity mapping, or availability assertion produces a new observation.
The payload hash detects unchanged content across runs. This defines identity;
step 2 implements immutable storage and per-task observation deduplication.
Logical-record/version selection across runs remains later curation work.

Payload hashes cover parsed JSON, not original HTTP bytes. If exact source
documents or responses need retention, the storage stage must preserve them
separately with their own byte hashes and references.

## Validation and versioning

Dependencies are listed in `requirements.txt`. The validator makes no network
requests and does not load credentials or write files.

```bash
python3 -B validate_research_data.py
python3 -B validate_research_data.py \
  --universe examples/research-contract/universe.json \
  --records examples/research-contract/records.jsonl
python3 -B -m unittest test_research_contract.py
```

The default command validates the pilot universe and taxonomy. The second
command validates the fictional fixture universe and all three observations.
`--records` is repeatable and accepts JSON or JSONL. Malformed input exits 1;
warnings, including provisional entities, are reported separately.

Validation checks schemas, real calendar dates, time precision, validity
intervals, duplicate IDs, dangling references, relation endpoint types,
subsector membership, potentially conflicting verified listings/external IDs,
availability evidence, hashes, and duplicate observations within supplied
record files. It does not verify external facts, alias truth, global source
coverage, or point-in-time model eligibility. Nine existing collector test
files do not establish those properties either.

Version the universe whenever its assertions change; preserve previous files
and stable entity IDs. Increment taxonomy versions when classification rules
change. Breaking record changes require a new `schema_version` and explicit
migration. Fictional examples use universe version `0.0.1` and must never enter
production data; the actual provisional pilot uses `0.1.0`.

## Next review point

The shared storage layer and SEC pilot are implemented; review
`SEC_COLLECTION.md` before step 4's remaining collector migrations. New company discovery, source fact
verification, and broader historical entity curation remain work beyond this
seed import.

## USPTO prosecution document datasets

`uspto_odp/patent_office_actions` and `uspto_odp/patent_petition_decisions`
use the shared collected-record envelope plus
[the prosecution payload schema](schemas/patent-prosecution-payload.schema.json).
`research_contract.validate_record` enforces this schema during page commits and
curation. Source record identity is the provider action/decision identity;
application number is a join key, not a unique document key. Official-document
identities remain separate for cross-feed evidence correlation.

API responses, document metadata and PDFs use content-addressed
`source_documents/uspto_odp/<sha256>` keys. Download state lives under
`checkpoints/uspto-prosecution-documents/`; stable first observations are under
`checkpoints/uspto-prosecution-first-observed/`. Each successful PDF carries its
original official URL, document identity, hash and byte count. Credentials and
signed redirect URLs are not written to evidence. Partial document retrieval
cannot advance the source page or produce a completed-window release.

Historical, update and reconciliation tasks retain distinct scope/checkpoints.
Reconciliation publishes additional observations, not additional occurrences;
consumers deduplicate by application/official-document identity and select
versions using their evidence cutoff. Public availability remains unknown and
published observations are not automatically eligible for historical models.
See [prosecution operations](PATENT_PROSECUTION_OPERATIONS.md).
