# Full raw-data source audit — separate chat handoff

Prepared 30 October 2026. This defines a separate audit workstream so the parent
chat can return to building `metadata_engine`. The audit has not yet been run
across all sources. Creating this file does not create a chat branch.

## Objective

Check every catalog entry for the original substantive data needed for later
processing. Distinguish what the provider makes available, what the collector
requests, what is actually archived, and what downstream tables expose.

Use all 158 entries in `config/constellation-source-registry.json` as the
inventory and reconcile them to `/home/ec2-user/data-source-status-2026-10-26.md`.
The status filename is retained from October 26; its content was refreshed on
October 30. A catalog entry is not necessarily an independent provider.

## Meaning of full raw data

- Filings: original complete filing/submission and required exhibits or other
  linked documents, rather than filing indexes, extracted dates or summaries.
- Research: full original paper/preprint, applicable supplements and linked
  substantive artifacts where accessible. Abstracts and bibliographic records
  provide discovery only. Do not claim every publisher offers full text.
- Patents: original specification, claims, drawings and relevant legal or
  prosecution documents for the declared dataset; bibliographic records alone
  do not establish these are captured.
- Trials/regulatory/grants/procurement: full provider record and required linked
  protocols, results, decisions, award terms or attachments for the declared
  record type. Missing or restricted documents remain explicit gaps.
- Statistical, market, climate, trade and geospatial sources: complete native
  API observations/files for the declared scope, including dimensions, units,
  flags, definitions and revision/vintage information when available. A native
  numeric dataset is substantive raw data; it need not have a narrative PDF.
- News, social and web records: original available body/content and relevant
  attachments/media for the declared dataset; title/date/URL lists alone fail.
- Provider metadata may describe or locate a source, but must not substitute
  for the underlying content. Preserve the distinction between an original
  publisher record, a normalized envelope, and third-party analysis.

Raw completeness is scoped: one complete document does not certify a source,
its entire archive, every geography, or original historical vintages.

User clarification, 30 October: treat **EODHD separately** as company-reference
and stock-market vendor data. For `eodhd`, validate the complete returned
`General` company-profile section and exchange listing responses for their
declared scope; do not require original filings or full unfiltered fundamentals.
For `eodhd_market`, validate native dated prices/OHLCV, adjustment fields,
dividends and splits. Preserve archived provider responses and provenance,
identify descriptions/classifications as vendor claims, and keep current
adjustments distinct from original historical vintages. Absence of primary
company documents is not a completeness failure for these declared datasets.
Bad/corrupt responses, identity mismatches and missing required observations
still fail. See `METADATA_ENGINE_OPERATIONS.md` for deployed contract 2.0.3 and
the bounded m7i replay receipt; its three samples do not certify the corpus.

## Audit method and outputs

1. Reconcile the 158-entry inventory with collectors, contracts and saved
   collection manifests. Include paused, unavailable and access-layer entries.
2. Inspect current code and bounded committed S3 samples before requesting new
   data. Verify checksums and that the artifacts actually contain substantive
   content rather than HTML block pages or discovery/catalog pages.
3. Check official provider documentation for full-content routes, attachments,
   bulk downloads, permitted access and historical scope. Record evidence URLs.
4. Use bounded live probes where needed, respecting existing credentials,
   provider budgets, owner pauses and known licence restrictions. Do not restart
   paused sources, buy access or change production schedules as part of checking.
5. Record per-source/dataset requirements, observed content, completeness,
   missing artifacts, and exact engineering/access actions. Preserve individual
   record/version evidence; partial or failed responses are not empty success.
6. Produce a machine-readable audit register and readable report. Every catalog
   entry must receive an outcome, including explicit `not_tested` where access
   or source restrictions prevent verification.

Recommended register fields:

```text
catalog_entry, source_key, dataset, provider_role,
required_raw_artifacts, provider_full_content_available,
collector_requests_full_content, archive_contains_full_content,
sample_manifest_uri, sample_raw_uri, sample_sha256,
sample_identity, sample_bytes, sample_validation,
missing_artifacts, access_or_license_constraint,
historical_scope_verified, original_vintages_verified,
outcome, next_action, official_evidence_urls, checked_at
```

Outcomes: `verified_sample_complete`, `partial_content`, `metadata_only`,
`access_blocked`, `owner_paused`, `unavailable_with_evidence`, `not_tested`,
or `access_layer_only`. Keep provider availability and actual saved content as
separate findings. A complete sample retains the sample qualification.

## Existing proof: bounded SEC pilot

Read `METADATA_ENGINE_SEC_DOCUMENT_PILOT.md` and the retrieval implementation in
`metadata_engine/sec_documents.py`.

- Accession `0000950170-24-067660`, CRISPR Therapeutics AG, 8-K.
- Original SEC submission downloaded on m7i, 931,431 bytes, 11 embedded documents.
- Accession/CIK/form, structural completeness and independent S3 read-back
  checks passed. SHA-256:
  `ca11cb9b18e68330810e97f392f72c3051eaaa1900117053e9cca7580a927e21`.
- One isolated pilot passed; no general SEC/corpus completeness claim follows.
- Europe PMC's current initial contract only requires `provider_record` and
  needs strengthening to require original full content before acceptance for
  this user's publication-processing objective.

## Parent metadata-engine state

- Existing RDS MySQL instance: `semaphore`; new database: `metadata_engine`.
- 13 tables installed. Four rows each in `source_contracts` and
  `source_raw_requirements`; other tables were empty at the last live inspection.
- Initial contracts: SEC EDGAR, FDA openFDA, EIA retail prices and Europe PMC.
- Dedicated m7i worker credential: Secrets Manager `metadata-engine/worker`.
  Never print secret values. The worker has SELECT/INSERT/UPDATE on this new
  database; the existing queue uses separate `constellation_operations`.
- `tracking` was dropped after encrypted RDS snapshot
  `semaphore-pre-metadata-reset-20261030` reached `available`.
- m7i worker: `i-06241bd1c4e91c2fc`; t3 controller: `i-070bab0b09f794629`.
- Full source-audit findings should feed revised contracts and bounded tests
  before rollout to captured history or all new inputs.

## Starting prompt for the fork

Read `data-collection-processing/RAW_SOURCE_AUDIT_HANDOFF.md` and audit all 158
catalog entries for full original raw-data availability and actual capture.
Work through the register with bounded evidence checks; report partial content,
metadata-only routes, access limits and exact next actions. Preserve owner
pauses. Return a report and machine-readable register for the metadata-engine
chat to use when revising source contracts. Start the audit now.
