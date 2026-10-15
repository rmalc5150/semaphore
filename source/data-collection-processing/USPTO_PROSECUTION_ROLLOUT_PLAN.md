# USPTO examination and petition evidence rollout

Collector/storage implementation started October 14, 2026. The two source adapters, payload schema, original-PDF retention, resumable historical/incremental operations and typed observation publisher are implemented. The historical pilot has committed evidence from January 2021 and the hourly collector timer is enabled. See [operations and execution status](PATENT_PROSECUTION_OPERATIONS.md). Downstream entity/event processing remains proposed; this document does not establish complete source coverage or model eligibility.

Extend the existing patent collection system with public Office Actions and final Petition Decisions. Collect historical evidence as well as subsequent additions and corrections. Feed committed releases into [company/product discovery](ENTITY_DISCOVERY_ROLLOUT_PLAN.md) and the [event pipeline](event-pipeline.md); reuse source evidence rather than building separate downloaders for each consumer.

## Historical scope and coverage

Use the current January 1, 2021 collection start in `config/historical-collection.json`; this supersedes the older January 2015 patent proposal. Model eligibility remains a separate, evidence-based decision. Record an explicit exclusive end date for every backfill plan. Do not silently expand collection to all history since 2001.

Partition historical work by the source's documented Office Action/decision date, not application filing date. Include in-range documents for older applications wherever public source coverage permits. Record filing-year restrictions separately: USPTO describes these offerings as covering patents and published applications filed since 2001, and petition coverage is incremental. Date-undetermined documents belong in a separate discovery cohort with unknown historical availability.

Before implementation, inspect current official API schemas, release notes, authentication, filters, stable identities, pagination, document retrieval, update semantics, quotas and actual coverage. Test a bounded cohort against original application documents. Office Action search, structured rejection/citation APIs and petition search may have different date ranges and delays; do not assume they share coverage or freshness. If a feed lacks an update cursor, specify bounded overlap and periodic older-window reconciliation. If date filtering cannot enumerate the required history, record that limitation and validate an application-based or bulk alternative before claiming completeness.

Existing application/publication/assignment backfill receipts do not establish coverage for either new dataset. Track source-supported coverage, completed queried windows, missing documents and unmatched applications independently. A complete query means enumeration within the declared source scope, not every US prosecution document. Historical imports retain today's capture time and do not establish historical registry membership or point-in-time availability.

## Collector and storage contracts

Extend `patent_collection.py` and the existing storage/checkpoint mechanisms with separate datasets `patent_office_actions` and `patent_petition_decisions`. Reuse the existing API-key loader where supported by the verified endpoint. Preserve exact API responses and original document bytes with checksums; downloads and extraction receive their own bounded, resumable task state. A search row whose document download failed must expose that failure rather than imply complete evidence.

Each observation carries provider/dataset, stable source document identity, normalized US application identity and original identifier, publication references where supplied, document type, source action/decision date and precision, source public-availability evidence, provider update time where documented, first observation/capture time, raw references/hashes, document retrieval status, extraction version and supporting page/passage. Preserve multiple actions per application. Do not use application number alone as a document key. Validate provider identities; when absent, define and collision-check a deterministic identity from documented immutable fields. Hashes identify content versions, not automatically distinct events.

Keep structured source fields separate from extracted claims: rejection grounds and affected claims, cited references, petition consideration and outcome are populated only where supported. Preserve unknowns and reported parties' roles. A cited patent or organization is a reference, not the owner of the examined application. Retain unresolved company/product matches for discovery.

Use independent per-dataset/date-scope checkpoints, manifests and complete/partial/failed outcomes. Bound requests, pages, download bytes and extraction work; obey shared USPTO quota controls across collectors. Resume partial work without repeating successful downloads. Validate pagination and source mutation behavior before advancing checkpoints. Corrections append observations; reconciliation must not overwrite retained evidence.

Publish typed Office Action and Petition Decision observations and their document/citation relationships into versioned Athena releases using existing committed-release validation. Typed observation contracts use `optima_patent_office_actions` and `optima_patent_petitions`, with application/document IDs, dates, status and source fields alongside full observation lineage. Complete windows follow the existing verified publication process; operational status determines which releases are actually live. Preserve the current application/publication/assignment contracts and joins; adding these datasets does not authorize downstream schema assumptions.

## Historical-to-incremental rollout

1. Validate source contracts and coverage with a bounded pilot containing older applications, multiple documents, unresolved parties and missing-download cases. Record quotas, response sizes, actual document dates and source lag.
2. Implement adapters, original-document retrieval and typed publication. Verify meaningful failure/recovery behavior: interrupted pages/downloads, mutation during enumeration, corrections, duplicate documents across feeds and quota exhaustion.
3. Generate monthly historical tasks from January 2021 through a pinned exclusive cutoff. Adjust partition size to measured volume. Report each dataset's progress and gaps independently of the existing patent backfill.
4. Capture incremental additions/updates from the pinned cutoff while historical work proceeds, within shared resource budgets. Validate overlap and cutover reconciliation; keep historical completion and incremental freshness separate. Enable recurring work only after the bounded pilot and recovery checks pass.
5. Replay committed historical releases through discovery and event adapters with stable trigger identities. Historical replay must not label old actions as new occurrences. Publish coverage-aware downstream snapshots; model eligibility requires independently verified availability evidence.

## Downstream acceptance

Patent-led discovery uses examination text and references to nominate technical research, applicant/assignee resolution and product/program links. Company-led discovery searches the same retained evidence by resolved legal names, aliases and application identities to enrich initial inventories. Neither route automatically creates a company/product from every document, citation or rejection.

An Office Action can establish a specific examination milestone; a petition decision can establish a procedural outcome. They do not alone establish grant, application failure, ownership, product discontinuation, commercial viability or predicted impact. Related publications, actions, responses and decisions remain distinct milestones. Cross-feed copies of one official document share provenance and must not inflate evidence counts.

Accept the rollout when historical windows and gaps are accounted for, source documents and joins are auditable, retry/correction/cutover behavior is verified, both discovery routes consume the added evidence, and event replay preserves occurrence, availability and observation dates. Measure reviewed discovery yield and attribution errors alongside coverage, freshness and workload.

## Official references

- [USPTO Office Action APIs moved to ODP, March 26, 2026](https://content.govdelivery.com/accounts/USPTO/bulletins/40fd1a0).
- [Office Action Search](https://data.uspto.gov/office-actions).
- [Final petition decisions and incremental coverage](https://www.uspto.gov/learning-and-resources/ip-policy/foia-reading-room/final-decisions-commissioner-patents).
- [Petition Decisions](https://data.uspto.gov/petitions/petition-decisions).

These references establish the offerings; current endpoint schemas, coverage and access remain implementation checks.
