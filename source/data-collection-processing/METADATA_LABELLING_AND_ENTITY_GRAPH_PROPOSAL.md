# Metadata labelling and entity-trajectory proposal

Status: **proposal only**.  It does not change collectors, data stores, AWS
resources, raw objects, or published Athena tables.  The purpose of the pilot
is to prove the design on a bounded set of already committed records before it
is used for all newly captured or historical data.

## 1. Outcome

Create an evidence-preserving data layer that makes each published source
observation self-describing and makes entity roles traceable through time.

The design deliberately separates four things:

1. **Raw evidence** — immutable original responses, documents, and files.
2. **Labelled source observations** — a source record plus deterministic
   provenance, time, quality, and normalization labels.
3. **Canonical entities and events** — reviewed or provisional links across
   sources, held in RDS with supporting evidence.
4. **Analytical releases** — versioned Athena tables derived from those first
   three layers.

Semiotic processing is not included.  The system records document structure
and quoted/evidence locations, but does not infer narrative meaning, sentiment,
novelty, claims, or contradictions from prose.

## 2. Architecture

```text
collector or historical inventory
             |
             v
raw S3 objects + immutable collection manifests
             |
             v
Metadata Labelling Engine
  validate -> normalize -> evidence/time labels -> entity assertions
             |                                   |
             |                                   v
             |                         RDS PostgreSQL control and
             |                         canonical entity/event graph
             v
labelled immutable S3 release (Parquet)
             |
             v
Athena labelled and curated tables
```

S3 remains the location of original bytes.  Raw material is never edited to
attach labels.  A labelled record instead contains the raw S3 URI and byte
checksum that identify its evidence.

The current RDS MySQL 8.4 instance is the small transactional system of record
for collection state, licences, coverage, entity identities, candidate matches,
event links, and review decisions.  Athena is the read-heavy analytical interface.  It is
not the authority for unfinished, failed, empty, blocked, or unpublished work.

The existing `research_contract.py`, collected-record envelope,
`collection_storage.py`, immutable manifests, page receipts, task checkpoints,
and watermarks are the intended starting point.  The new engine consumes only
records that a committed manifest references.

## 3. Storage layers

| Layer | Location | Purpose | Mutability |
|---|---|---|---|
| Raw | Existing S3 raw prefixes | Original HTTP bytes, JSON, CSV, XML, PDFs, workbooks, headers and retrieval evidence | Immutable |
| Manifest/control | RDS plus existing immutable S3 manifests | Source configuration, raw-object inventory, runs, windows, coverage, publication and licences | Versioned; limited operational heads may change |
| Labelled observations | S3 Parquet/Iceberg-backed Athena tables | Self-describing normalized source records; no inferred cross-source truth | Immutable releases |
| Canonical graph | RDS PostgreSQL | Entity identities, aliases, relationships, canonical events, evidence and resolution decisions | Append/version, not destructive overwrite |
| Curated analytics | Athena Iceberg tables/views | Point-in-time entities, event roles, measurements and current-state views | New snapshots/releases |

The first labelled tier should be append-only Parquet releases.  Curated tables
that need controlled current-state selection or correction may use Athena
Iceberg.  Raw data must not be updated through Athena.

## 4. Metadata Labelling Engine

### Responsibilities

For every accepted source observation, the engine:

1. verifies its committed input manifest and raw-object reference;
2. applies the source's explicit adapter contract;
3. validates and normalizes deterministic fields while preserving originals;
4. emits document/table/row/page evidence locators where available;
5. attaches provenance, time, licensing, quality and release labels;
6. creates direct identifier assertions and unresolved/candidate entity links;
7. writes an immutable labelled release;
8. reconciles counts, hashes and representative Athena queries; and
9. registers the verified release and coverage result in RDS.

It does not discard a record merely because entity resolution is uncertain.
Unresolved records are labelled as unresolved or linked to a provisional
entity.  It also does not treat a failed request as an empty result.

### Package shape

```text
metadata_engine/
  core/
    inventory.py           # committed-manifest and legacy inventory readers
    envelope.py            # common labels, identity and canonical serialization
    validation.py          # schema and cross-field validation
    normalizers.py         # dates, units, currencies, IDs, languages, geography
    lineage.py             # raw/evidence/release links
    rds_registry.py        # transactional control-plane writes
    publication.py         # immutable release preparation and verification
    athena.py              # table/view deployment and read-back checks
  adapters/
    api_records.py
    time_series.py
    documents.py
    filings_xbrl.py
    publications.py
    patents.py
    grants_procurement.py
    geospatial_assets.py
  contracts/
    <source_key>.yaml
  schemas/
    labelled-observation.v1.json
    <record-kind>.v1.json
```

The adapter library is deliberately compact.  Source variation belongs mostly
in versioned declarative contracts; code is added only where parsing mechanics
materially differ.

### Adapter families

| Adapter | Primary source shapes |
|---|---|
| `api_records` | Registry, regulatory, directory, platform and ordinary JSON APIs |
| `time_series` | Economic, trade, price, weather, production and energy observations |
| `documents` | PDFs, HTML archives, reports, web captures and document indexes |
| `filings_xbrl` | SEC, EDINET, HKEX, CNINFO, OpenDART and MOPS filings/facts |
| `publications` | Publications, preprints, datasets, software and citations |
| `patents` | Patent, legal-event, assignment and prosecution sources |
| `grants_procurement` | Grant, award, opportunity and procurement records |
| `geospatial_assets` | Facilities, mines, plants, vessels, ports and asset/location feeds |

## 5. Source contract

Each source has a reviewed, versioned contract.  It makes the source-specific
decisions explicit and testable.

```yaml
source_key: sec_edgar
adapter: filings_xbrl
contract_version: 1.0.0

identity:
  source_record_id: accession_number
  basis: provider

time_mapping:
  event_at: filing_date
  source_published_at: acceptance_datetime
  available_at:
    field: acceptance_datetime
    basis: provider_metadata

outputs:
  - record_kind: filing
    payload_schema: schemas/filing.v1.json
  - record_kind: filing_fact
    payload_schema: schemas/filing_fact.v1.json

evidence:
  document_locator: filing_url
  row_locator: xbrl_context_or_fact_id

normalization:
  identifier_namespaces: [CIK, accession_number]
  currency: ISO_4217
  units: xbrl_units
  timezone: America/New_York

quality_rules:
  - accession_matches_source_id
  - accepted_at_not_before_filing_date
  - required_filing_fields_present

publication:
  partition_by: [source_key, record_kind, available_year, available_month]
```

Every contract must specify:

- source/dataset identity and adapter family;
- provider identity rule and immutable record-key basis;
- accepted inputs and payload/output schemas;
- source-to-common metadata field mappings;
- timezone, date precision, units, currency, geography and classifications;
- availability-time policy and evidence requirement;
- document or row-level evidence location;
- deterministic identifier namespaces and permitted candidate matching;
- quality/reconciliation rules, licences and retention policy; and
- output types and partitioning strategy.

## 6. Labelled observation contract

Each row in `source_observation` contains common queryable labels plus an
unchanged normalized source payload.  It retains rather than substitutes
original representations.

```text
record_id, observation_id, record_kind
source_key, dataset, source_record_id, source_record_id_basis
source_published_at, available_to_market_at, availability_basis
event_start_at, event_end_at, observation_start_at, observation_end_at
retrieved_at, first_seen_at, source_updated_at, date_precision, timezone
raw_s3_uri, raw_sha256, source_document_id, original_url, evidence_locator
schema_version, contract_version, adapter_version, parser_version
entity_match_status, direct_identifier_assertions
license_policy_id, allowed_uses, retention_policy
quality_status, quality_flags, extraction_confidence
ingest_run_id, release_id, payload_json
```

The logical ID and source-observation/version identity continue to use the
existing deterministic record/observation rules.  A changed payload, retrieval,
mapping, availability assertion, or entity mapping creates a new observation;
it does not overwrite the old one.

Typed Athena tables then promote frequently queried fields:

```text
documents, measurements, filings, filing_facts, publications,
patent_events, trials, grants, facilities, shipments, entity_identifiers,
entity_resolution_candidates
```

## 7. Lean RDS control plane and entity graph

Use a dedicated MySQL database (`metadata_engine`) on the existing RDS instance
rather than mixing the new control plane with the retired `tracking` schema.
This preserves transactions and foreign keys across lineage and entity
resolution while keeping the reset boundary clear.

```text
registry      source, source_contract, adapter_release, ingest_run,
              raw_object, source_window, publication_release,
              publication_member, licence_policy
quality       quality_assessment, coverage_assessment, dedupe_decision
identity      entity, entity_identifier, entity_name, security, listing,
              entity_relationship
resolution    entity_assertion, resolution_candidate, resolution_decision
events        canonical_event, event_version, event_participant, evidence
series        series_definition, series_observation, series_vintage
```

The database holds references and decisions, not copied raw payloads or the
entire analytical corpus.

### Entity identity and history

`identity.entity` assigns a permanent `ent_<uuid>` to organizations, people,
securities, products, facilities, technologies, patents, publications, trials,
grants, vessels and locations.  Its lifecycle state is `provisional`, `active`,
`merged`, `split`, or `retired`.  IDs are never regenerated from a name.

`entity_identifier` stores a namespace, value, validity interval, source
observation, evidence, confidence and review status.  Direct identifiers take
precedence: LEI, ROR, DOI, PMID, patent family, trial ID, IMO, facility ID,
ISIN and FIGI.

`entity_name` preserves original spelling, normalized form, language/script,
name kind, validity, source observation and evidence.  It supports former
names, legal names, trade names, abbreviations and transliterations without
assuming they all identify the same entity.

For securities, model a security separately from its issuer and exchange
listing:

```text
security --issued_by--> organization
listing  --lists-------> security
listing = exchange MIC + ticker + valid_from/to + evidence
```

A bare ticker is never a join key.

### Relationships and roles through time

Every business/person/facility relationship is an evidenced temporal assertion:

```text
entity_relationship
  subject_entity_id
  predicate                 subsidiary_of | owned_by | employed_by | operates |
                            manufactures | develops | licenses_in | ...
  object_entity_id
  valid_during              when true in the world, if known
  known_during              when knowable from available evidence
  source_observation_id
  evidence_id
  confidence, review_status
```

The entity/event link is equally important:

```text
event_participant
  canonical_event_id
  entity_id
  role                      issuer | filer | sponsor | applicant | inventor |
                            assignee | regulator | acquirer | target | buyer |
                            seller | operator | manufacturer | recipient |
                            vessel | origin | destination | ...
  role_during
  known_during
  source_observation_id
  evidence_id
  confidence, review_status
```

This supports trajectories such as: which facilities a company operated during
a period, which subsidiary filed a report, which issuer/security was affected,
or which organizations independently participated in an event.  A subsidiary
event remains its own event; any parent exposure is a separately queryable
relationship path, never an automatic attribution to the parent's stock.

Both `valid_during` and `known_during` are required concepts:

- **valid time**: when an entity relationship or event applied in the world;
- **knowledge/availability time**: when the information was publicly available
  or first observable to this system.

Point-in-time research must filter both.

## 8. Deduplication and versioning

Deduplicate at separate, explicit levels.  No level substitutes for another.

| Level | Match key / rule | Preserve |
|---|---|---|
| Raw object | SHA-256 of original bytes | Every retrieval, URI and header set |
| Source record/document | Source namespace + stable provider ID + content/version hash | Every provider revision and source record |
| Canonical document | Exact/structured document fingerprint, source identity and edition | Alternate locations and editions |
| Canonical event | Event type + participants/roles + time/place + stable event key when available | Independent evidence and event versions |
| Statistical series | Series definition/dimensions + observation period + vintage | Releases, revisions and restatements |

Three syndicated stories can be three documents and three source observations
but only one candidate canonical event with three evidence links.  Conversely,
similar-looking items remain separate where the evidence cannot justify a
link.

Corrections, amendments, restatements and retractions create new
`event_version` or series-vintage rows with explicit supersession links.
Conflicting evidence is retained as competing assertions; no universal truth or
reliability score is manufactured.

## 9. Processing paths

### New data

```text
collector commits a bounded page/window
  -> manifest-triggered labelling job reads committed records
  -> adapter produces labelled observations and resolution assertions
  -> immutable S3 release is written
  -> RDS transaction registers quality, coverage and release members
  -> Athena read-back/count verification passes
  -> release is marked published
```

`observation_id` is the idempotency key.  Retrying the same work cannot produce
duplicate observations.  A source revision is retained as a new version.

### Historical data

1. Inventory existing raw objects and committed manifests by source, dataset,
   format, date range and existing contract version.
2. For legacy objects without manifests, create a versioned `import_inventory`
   record; do not pretend unverified recursive S3 listings are complete.
3. Plan bounded jobs by source/dataset/adapter/contract/date window.
4. Label only that bounded input, reconcile input/accepted/quarantined counts,
   and publish an immutable release.
5. Record partial, failed, empty, blocked and accepted-unavailable windows in
   RDS; they remain visible for repair.
6. Re-run only source/window/contract cohorts affected by a later parser or
   contract release.  Keep earlier releases.

Historical processing and ongoing collection use exactly the same engine and
contracts.  They use separate checkpoints and watermarks.

## 10. Quality gates

A release may be registered as `published` only when it has:

- a committed input manifest or reviewed legacy inventory;
- valid contract/schema and stable source identity;
- raw S3 URI/checksum for every labelled observation;
- explicit time precision and availability basis, or an explicit unknown;
- evidence locator when the source format supports one;
- accepted/rejected/quarantined counts that reconcile to input;
- a source-window coverage state;
- entity decisions marked direct, candidate, provisional or unresolved;
- immutable output manifest and release checksum; and
- successful Athena read-back checks for count, partition, identity and sample
  provenance.

Failure at any gate does not delete prior successful data.  It leaves an
auditable failed or partial release/job and a precise retry scope.

## 11. Pilot and rollout

### Pilot goal

Prove that the engine can label, resolve and publish a bounded sample while
preserving evidence and historical time semantics.

### Pilot sources

Use four contrasting sources already represented by structured collection and
Athena work:

1. **SEC EDGAR** — filing/document identity, CIK, issuer/security links and
   XBRL facts.
2. **FDA/openFDA or EMA** — regulator/product/sponsor/status history.
3. **EIA or CAISO** — time series, units, geography and observation revisions.
4. **Europe PMC or DataCite** — DOI/PMID/ROR, publication versions and
   contributor roles.

Each pilot scope should be small and explicitly bounded.  It must include at
least one revision, one unresolved entity, one direct identifier match, and
one empty/failed or partial collection-window fixture in tests.

### Pilot acceptance tests

- Raw byte checksum and URI trace from Athena row to original evidence.
- Repeat run is idempotent.
- Changed source revision creates a new observation/version, not replacement.
- Same legal entity with a name change retains its canonical ID.
- Ambiguous name creates candidates/provisional entity, not a forced match.
- Exchange-qualified ticker query returns the correct historical security.
- Subsidiary event and parent relationship remain distinct in an event-role
  trajectory query.
- Point-in-time query excludes information unavailable at the requested cutoff.
- Partial/failed/empty window status is visible even when it emits zero rows.

### Rollout order

1. Approve this proposal and common labelled-observation contract.
2. Add RDS migrations and offline adapter/validation tests; no production
   writing yet.
3. Run the four-source bounded pilot in an isolated release namespace.
4. Review test results, RDS schema, Athena query cost and operator workflow.
5. Enable the engine for new data from successful source families.
6. Backfill committed history family by family, prioritizing structured sources.
7. Add document-heavy, OCR and geospatial adapters after the basic evidence
   and temporal model is proven.

## 12. Decisions deferred for discussion

- Exact RDS deployment: PostgreSQL RDS versus Aurora PostgreSQL.
- Iceberg from the first curated release versus append-only Parquet followed by
  an Iceberg migration.
- Human review interface and reviewer authorization model.
- Candidate-match scoring methods and thresholds.
- Canonical event matching rules by source family.
- Retention periods and licence enforcement implementation.
- Event-role vocabulary governance and classification-version registry.

Those choices should be made before production rollout, but none blocks the
offline contract, schema and pilot-test work.
