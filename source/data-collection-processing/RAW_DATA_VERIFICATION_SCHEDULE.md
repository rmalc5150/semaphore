# Daily raw-data and Athena verification schedule

This weekday-only schedule starts **Monday, 9 November 2026** and covers all 158 catalog entries in `config/constellation-source-registry.json`: 15 entries per weekday, with the final day containing 8. It retains registry order so every item can be reconciled directly to the catalog.

Live metadata-engine status was read on **9 November 2026**. “Raw stopped” means the engine has observed four consecutive raw-validation failures. “Owner paused” and “access layer” are intentional operating states, not raw-capture failures.

## How to verify an item

1. Open the listed raw S3 prefix and inspect a current native object and its collection manifest. Confirm provider identity, substantive content, MIME/type, checksum, and dataset scope. A discovery page, index, abstract, or summary is not raw completion.
2. Run the source-specific Athena query in workgroup `optima-collected-data`. It reports observations, unique linked raw objects, complete raw-status rows, and ingestion dates.
3. Record the exact inspected object URI, checksum/version, query execution ID, row counts, and outcome in the source audit register. A zero-row result or empty prefix is a finding to resolve, not a pass.

A checked **scoped pipeline review** records which provider fields or original documents passed. A bibliography-only review does not satisfy a full-patent-text requirement. Historical archive completion and unresolved commit dependencies remain separate checks.

## Schedule

### Day 1 — Monday — 9 November 2026 (15 catalog entries)

- [X] **1. GLEIF legal entities** (`gleif_legal_entities`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=gleif_legal_entities/`  
  Current collection state: **enabled — reviewed-source queue mode** — individual raw failures are recorded by collection date and do not stop GLEIF.  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record`; `public_capture_is_discovery_page_only` across 6 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `specialist_inputs`. Raw-content failures enter the GLEIF source/date queue; unexpected worker faults enter the pipeline-failure queue.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'gleif_legal_entities' GROUP BY source_key;`

- [X] **2. EOD Historical Data company profiles and listings** (`eodhd`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=eodhd/`  
  Current collection state: **enabled — reviewed-source queue mode** — EOD profile/listing collection timers are enabled and active; individual raw failures are recorded by collection date and do not stop this source.  
  Recorded raw-data errors: `eodhd_inventory_payload_differs_from_provider`; `missing_verified_raw_artifacts:provider_record` across 6 failed attempt(s).  
  Current raw processing: Archives complete EODHD `General` profiles and exchange listings; normalizes company identity while retaining provider fields. Raw-content failures enter the EOD source/date queue; unexpected worker faults enter the pipeline-failure queue.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'eodhd' GROUP BY source_key;`

- [X] **3. EOD Historical Data market data** (`eodhd_market`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=eodhd_market/`  
  Current collection state: **enabled — reviewed-source queue mode** — market collection and market-publication timers are enabled and actively processing their backlog; individual raw failures are queued by collection date.  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` across 4 failed attempt(s).  
  Current raw processing: Archives native prices/OHLCV, adjusted close, volume, dividends, and splits; normalizes market observations while retaining provider fields. Raw-content failures enter the EOD Market source/date queue; unexpected worker faults enter the pipeline-failure queue. Curated prices are published to `optima_market_research.market_prices_windows`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'eodhd_market' GROUP BY source_key;`

- [ ] **4. HKEX prices** (`hkex_prices`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=hkex_prices/`  
  Current collection state: **enabled — reviewed-source queue mode** — individual raw failures are recorded by collection date and do not stop HKEX Prices.  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record`; `public_capture_is_discovery_page_only` across 7 failed attempt(s).  
  Current raw processing: Archives native observations with dimensions, units, flags, and timestamps; extracts normalized measurements for `market_records`. Raw-content failures enter the HKEX source/date queue; unexpected worker faults enter the pipeline-failure queue. Curated prices are published to `optima_market_research.market_prices_windows`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'hkex_prices' GROUP BY source_key;`

- [X] **5. US SEC filings (including Form D and crowdfunding forms)** (`sec_edgar`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=sec_edgar/`  
  Current collection state: **enabled — reviewed-source queue mode** — SEC daily intake and committed-input processing are active; individual raw failures are recorded by collection date and do not stop SEC metadata processing.  
  Recorded raw-data errors: `sec_document_empty_or_oversized`; `sec_primary_document_missing` across 15 failed attempt(s).  
  Current raw processing: Archives the provider filing record plus original primary document; extracts filing identity, provenance, and normalized source-record fields for `filings`. Raw-content failures enter the SEC source/date queue; unexpected worker faults enter the pipeline-failure queue.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'sec_edgar' GROUP BY source_key;`

- [x] **6. SEC company financial facts** (`sec_companyfacts`)  
  Review: **reviewed by owner — 9 November 2026**.  
  Automated pipeline check: **9 November 2026** — source enabled, 464 accepted metadata jobs / 191 queued at the sampled check. Athena verified **8,439 raw-complete observations / 198 raw objects**; query `8806149a-dbc8-4c42-b802-43822f5f07b2`. Published ingestion dates currently extend through **26 October**; backlog/freshness checks remain separate from this review.  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=sec_companyfacts/`  
  Current collection state: **enabled — reviewed-source queue mode** — individual raw failures are recorded by collection date and do not stop this reviewed source.  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'sec_companyfacts' GROUP BY source_key;`

- [ ] **7. HKEX announcements** (`hkex_news`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=hkex_news/`  
  Current collection state: **enabled — repaired and resumed November 9**; consecutive raw failures reset after four validated production replays.  
  Recorded raw-data errors: Four earlier `missing_verified_raw_artifacts:primary_document` failures repaired; original failed reports retained. Athena verified **86 raw-complete row occurrences / 53 distinct filing IDs** in these four batches, query `063ba399-87f9-4036-a6f1-0f73b3922f4a`. This is a repaired sample, not complete history.  
  Current raw processing: Archives original PDFs/Office/HTML and provider records. English language-availability notices are retained separately; same-issuer/same-minute Chinese candidates are captured with their own HKEX IDs and explicit candidate provenance, without asserting translation equivalence. Chinese payloads and PDF evidence passed Athena inspection; English notice IDs returned zero substantive filing rows. Full Chinese-market coverage and English translations are not established. Owner review remains unchecked. [Repair evidence](repair-notes/2026-11-09-hkex-repair/README.md).  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'hkex_news' GROUP BY source_key;`

- [x] **8. Japan EDINET corporate filings** (`edinet_filings`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=edinet_filings/`  
  Review: **Owner reviewed November 9, 2026** — original provider artifacts and linked extracted content.  
  Current collection state: **enabled — reviewed-source queue mode**; individual raw failures remain recorded and do not stop the whole source.  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory; current processing and publication are checked separately.  
  Current raw processing: Archives the provider filing record plus original primary document; extracts filing identity, provenance, and normalized source-record fields for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'edinet_filings' GROUP BY source_key;`  
  November 9 live verification: **138 observations / 138 linked raw objects / 138 raw-complete observations** in Athena, query `bccb8a46-4dde-4ccd-b387-3585319bc50e`. Seven metadata retries caused by oversized derived extraction JSON were repaired and published; original provider artifacts remain required. Latest published `ingested_at` is November 1, so daily freshness and historical catch-up remain separate from your completed raw review. [Runtime check and evidence](repair-notes/2026-11-09-edinet-review/README.md).

- [x] **9. Disclosure candidates (internal route)** (`disclosure_candidates`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=disclosure_candidates/`  
  Review: **Owner passed raw-source review November 9, 2026**. Athena publication is a separate check.  
  Current collection state: **access_layer** in the metadata engine — derived internal route; published through the disclosure research tables, not `optima_metadata_engine.source_observations`  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `licensing_agreements, ma_announcements, press_releases, strategic_transactions`.  
  Athena SQL: `SELECT source, dataset, count(*) AS observations, count(DISTINCT record_id) AS distinct_records, count(DISTINCT raw_batch) AS raw_batches, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_disclosures_pilot.event_candidates_windows WHERE source = 'disclosure_candidates' GROUP BY source, dataset;`  
  Fresh Athena verification after restart November 9: **926 row occurrences** (licensing agreements 77, strategic transactions 281, press releases 318, M&A announcements 250). Latest published ingestion **November 9**, query `31d37081-537f-4666-8133-ae9891de3b6c`. The repaired October 16 window produced zero licensing candidates; its verified empty manifest is not a missing capture. Daily cursor advanced to October 17; historical cursor advanced to January 2, 2016. Both worker schedules are enabled; historical completion is still pending. [Restart evidence](repair-notes/2026-11-09-disclosure-resume/README.md).

- [x] **10. Disclosure documents (internal route)** (`disclosure_documents`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=disclosure_documents/`  
  Review: **Owner passed raw-source review November 9, 2026**. Athena publication is a separate check.  
  Current collection state: **access_layer** in the metadata engine — derived internal route; published through the disclosure research tables, not `optima_metadata_engine.source_observations`  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `documents`.  
  Athena SQL: `SELECT source, dataset, count(*) AS observations, count(DISTINCT record_id) AS distinct_records, count(DISTINCT raw_batch) AS raw_batches, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_disclosures_pilot.documents_windows WHERE source = 'disclosure_documents' GROUP BY source, dataset;`  
  Fresh Athena verification after restart November 9: **538 row occurrences / 288 distinct record IDs**; latest published ingestion **November 9**, query `869f71ef-f472-4fe5-94c7-354fb6d5f875`. Five new original-document/text records from October 16 were committed and published. Daily cursor advanced to October 17; historical cursor advanced to January 2, 2016. The backlog is not yet complete. [Restart evidence](repair-notes/2026-11-09-disclosure-resume/README.md).

- [x] **11. Finlight news** (`finlight`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=finlight/`  
  Review: **Reviewed November 9, 2026 after capture/metadata/Athena verification.**  
  Current collection state: **enabled — reviewed-source queue mode**, contract `2.0.3`; individual failures remain logged without stopping the entire source.  
  Recorded raw-data errors: Earlier failures were caused by an empty provider-host allowlist and a generic validator that could not establish news-provider evidence. Original reports retained; 235 old-version jobs superseded/requeued under the new immutable contract.  
  Current raw processing: Checks original Finlight API JSON, checksum, exact article URL/identity and provider fields; request receipts are rejected. Publisher HTML/full text is separate evidence, not implied by provider-record completeness.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'finlight' GROUP BY source_key;`  
  November 9 Athena verification: **160 raw-complete observations linked to five raw batches**, including current-day capture; query `a6756902-682c-4c43-9ad8-3d395205e8d3`. Curated `optima_news_research.news_articles_windows` also verified: **13,740 distinct articles**, latest ingestion November 9; query `b0b7aafb-ae73-4f63-90bf-e395dabf88c1`. Published a fully completed November 3 window with all eight sector/language manifests. Metadata backlogs, full text and complete history remain separate checks. Verified archive scope begins January 2021; pre-2021 access remains unverified. Historical capture is running from its retained November 10, 2021 checkpoint; publisher full-text gaps remain explicit. [Repair evidence and schedules](repair-notes/2026-11-09-finlight/README.md).

- [ ] **12. Marketaux news (paused)** (`marketaux`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=marketaux/`  
  Current collection state: **owner_paused** — deliberate pause, not a raw-validation stop  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `news_articles`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'marketaux' GROUP BY source_key;`

- [x] **13. People-related RSS feeds** (`people_rss`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=people_rss/`  
  Review: **Reviewed November 9, 2026 after live body capture, metadata replay and Athena payload checks.**  
  Current collection state: **enabled — contract 2.0.3, reviewed-source queue mode**. Missing bodies are separate article gaps, not raw-complete observations.  
  Current raw processing: Uses explicit RSS/Atom full content when substantive; otherwise retrieves publisher HTML and falls back to Decodo on nonrestricted retrieval/body failures. Saves original content, extracted text, hashes, chunks and retrieval provenance. Paywalls/access restrictions, missing pages and rate budgets remain explicit; there is no guarantee that every article is obtainable. Independent worker retries saved article gaps every two minutes, at most two articles per invocation, with bounded direct/Decodo budgets.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'people_rss' GROUP BY source_key;`
  
  Verified November 9: **42 full-text observations / five raw batches** returned by this metadata query, including a newly repaired record. Query `5449657c-d653-4638-8f08-05f7bd5eed9a`. Curated `optima_people_research.source_observations_windows` also returned the repaired article with **2,939 characters**, capture status `captured` and full-content S3 reference; query `2501b82d-f4ec-4ed6-9b3c-815f4c33018d`. A separate budgeted Decodo probe returned **2,945 characters**. **40 focused tests passed.** Backlog and unavailable articles remain separate from this reviewed sample. [Repair and evidence](repair-notes/2026-11-09-people-rss/README.md).

- [x] **14. Personnel announcement archives** (`personnel_archive`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=personnel_archive/`  
  Review: **Reviewed November 9, 2026 after committed-parent, original-content, metadata and Athena payload checks.**  
  Current collection state: **enabled — contract 2.0.3, reviewed-source queue mode**. Derived archive candidates retain their upstream source identity and original evidence.  
  Recorded raw-data errors: Earlier generic validation did not follow the nested parent record and had no provider-host route. Failed reports retained; 186 old-version jobs superseded/requeued. Missing/unsupported parent content remains an individual gap, not a verified complete record.  
  Current raw processing: Verifies archive-to-parent observation/record/URL identity, pinned parent-manifest SHA-256, committed parent batch and original content. Personnel relevance and entity matches remain unreviewed candidates; a raw-source review does not confirm personnel movements.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'personnel_archive' GROUP BY source_key;`
  
  November 9 verification: **nine raw-complete observations / five raw batches**, latest ingestion November 9; metadata query `7f68786a-d8ed-468c-9aff-9ed8828226d4`. Curated `optima_people_research.source_observations_windows` also returned a fresh archive record with **1,958 characters** and its full-text S3 reference, query `1c349958-d94a-4096-8d9e-48513f380301`. **37 focused tests passed.** Further archive backlog and unsupported upstream evidence remain separate checks. [Repair and runtime evidence](repair-notes/2026-11-09-personnel-archive/README.md).

- [x] **15. ClinicalTrials.gov** (`clinicaltrials_gov`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=clinicaltrials_gov/`  
  Review: **Reviewed November 9, 2026 after original API-response, metadata replay and Athena payload verification.**  
  Current collection state: **enabled — contract 2.0.3, reviewed-source queue mode**. Zero consecutive raw failures; retained batches continue through the queue.  
  Root cause repaired: The old generic contract had no permitted provider host and could not verify the saved API studies. New validation requires the official API host, matching NCT ID, full protocol/status sections and exact equality with the unmodified study response; projected/request-only responses cannot pass.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'clinicaltrials_gov' GROUP BY source_key;`  
  Verified **128 raw-complete observations / four linked raw batches**, including November 9 ingestion. Aggregate query `f5e0d698-fd4f-4d40-8aeb-4eca0a700370`; full metadata payload query `43701c23-9bf7-40ca-8ee3-5cde6669244a` returned `NCT05651932` and its complete protocol/provider evidence. **41 focused tests passed.** Current study versions are not historical snapshots; optional results exist only where the provider supplies them.  
  Curated `optima_regulatory_pilot.research_records_windows` also returned study IDs, titles, statuses and 13–15 KB payloads, query `22cad31b-c02c-4474-b7b9-0b9ec10b5e93`. Its latest checked observation remains October 15: **curated-window publication is behind the newly repaired metadata table**. Latest captured calendar window remains partial (300 records); neither source history nor all curated publication is marked complete. [Repair, query evidence and runtime checks](repair-notes/2026-11-09-clinicaltrials/README.md).

### Day 2 — Tuesday — 10 November 2026 (15 catalog entries)

- [x] **16. EMA Clinical Trials Information System** (`ema_ctis`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=ema_ctis/`  
  Review: **Reviewed by owner November 10, 2026; original API detail, metadata replay and Athena publication checks passed.**  
  Current collection state: **enabled — contract 2.0.3, reviewed-source date queues**. Daily capture and historical dispatch controls permit work; metadata timer is enabled and running.  
  Root cause repaired: Public discovery-page receipts had triggered the source-wide circuit breaker despite valid CTIS API records. Discovery pages remain explicit failures; they cannot become trial data or stop this reviewed source. Strict validation now matches the official detail response, CT number, original application/decision objects and event identity.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'ema_ctis' GROUP BY source_key;`  
  Verified **1,996 raw-complete observations / 84 linked raw batches**, latest ingestion November 9, query `b56daedd-f9be-4b08-92b8-c8f377c1c516`. Two new-version batches passed replay; **35 trial/event records** were also published into verified curated windows for November 6 and 8. **34 focused tests passed.** Full trial detail and matched events are saved; linked PDF/documents are a separate scope, not certified by this review. Current public versions are not historical snapshots; the 10,000-result search cap and delayed disclosure limit historical completeness. [Repair, payload queries and live health checks](repair-notes/2026-11-10-ctis/README.md).

- [x] **17. FDA openFDA** (`fda_openfda`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=fda_openfda/`  
  Review: **Reviewed November 10, 2026 after original-response validation, live approvals/CRL probes, metadata replay and Athena readback.**  
  Current collection state: **enabled — contract 2.0.3, reviewed-source date queues**, zero consecutive raw failures. Capture, publication and metadata timers are active; queued work continues.  
  Root cause repaired: Empty provider-host allowlist caused four valid saved batches to fail metadata validation. New validator requires official openFDA endpoints, exact complete application/CRL equality, matching approval submissions and composite/variant IDs. Aggregates, projections and request receipts cannot pass.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations" WHERE source_key = 'fda_openfda' GROUP BY source_key;`  
  Verified **75 raw-complete observations / five linked raw batches**, query `2864e5e7-cc4b-4155-8978-4a186907f778`; newest checked nonempty batch ingestion **October 31**. Full application/submission payload checks passed in metadata (`736673d7-4ddf-4ad9-87fc-6cb94d9be0a8`) and curated regulatory windows (`27b2ba9f-3d56-480f-8f18-4fc31cce5be3`). Published **14 regulatory records** for a complete October 23 window. **39 focused tests passed.** Live authenticated API probes succeeded November 10; the shared daily collector completed an empty October 24 window November 9 and retained an October 25 catch-up cursor. Review does not certify current-day freshness, full history, linked PDF downloads or point-in-time publication vintages. [Repair and live evidence](repair-notes/2026-11-10-openfda/README.md).

  **Rechecked November 10:** published two newly accepted batches; final query `214f3440-5582-4180-9ef6-660f1bc741f1` returned **108 raw-complete observations / seven raw batches**. Before that publication, fresh query `33f10377-35d6-43af-bfff-66d1318d843a` returned **75 observations / five raw batches**, with result reuse explicitly disabled. Use AWS account `059416028963`, region **US East (N. Virginia) / us-east-1**, data source **AwsDataCatalog**, workgroup **optima-collected-data**, and turn **Reuse query results** off before running again. The query above now explicitly names the catalog. An empty console result was not reproduced server-side; if it persists, retain that failing query's execution ID so its exact query/context can be compared. [Current query and engine checks](repair-notes/2026-11-10-openfda-recheck/README.md).

- [x] **18. Drugs@FDA applications** (`drugsfda_applications`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=drugsfda_applications/`  
  Review: **Reviewed November 10, 2026 after original application/product validation, metadata replay and fresh capture-to-Athena readback.**  
  Current collection state: **enabled — contract 2.0.3, reviewed-source date queues**, zero consecutive raw failures. The generic validator had rejected full application JSON; exact provider-result/application identity checks now validate every returned product and supplied submission without projecting fields.  
  Scope: **all provider applications/products**, without company, sector or active-marketing filters. Retains discontinued products. Existing dated historical and daily routes continue; a new independently bounded weekly inventory covers 30 application-number ranges plus their complement, including older applications outside recent date windows. Provider reported **29,447 applications** in the live probe; that is an application count, not a product count or a completion certificate.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations" WHERE source_key = 'drugsfda_applications' GROUP BY source_key;`  
  Verified **192 raw-complete observations / five linked raw batches**, including November 10 capture; query `0cdbc852-4f68-4c51-a761-1907da862c6e`. Fresh payload query `0456ddc9-397d-4d41-93ff-965ee551fff4` confirmed application IDs and one/two-product arrays; curated specialist payload query `6b581467-5ad3-48c0-943d-b67de608da58` also returned complete applications. **34 focused tests passed.** Inventory timer continues every two minutes, at most two scopes/four pages per scope under 384 MiB/20% CPU. It had committed **800 applications** at the recorded inventory checkpoint; full inventory/history remains incomplete. No new key is needed. This query is separate from `fda_openfda` and `ema_medicines`. Use us-east-1 / AwsDataCatalog / optima-collected-data, result reuse off. [Repair, all-provider inventory scope and verification](repair-notes/2026-11-10-drugsfda/README.md).

- [x] **19. EMA medicines** (`ema_medicines`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=ema_medicines/`  
  Review: **Reviewed November 10, 2026 after exact original-row validation, fresh full-report capture, metadata replay and Athena reconciliation.**  
  Current collection state: **enabled — contract 2.0.3, reviewed-source date queues**, zero consecutive raw failures. Generic substantive-content checks had rejected valid original medicine JSON; strict EMA product-ID/full-row/report-origin validation replaces that failure. Requeued 40 unfinished old-contract jobs; historical first-publication-date scopes continue as current-report observations, not historical vintages.  
  Scope: **all medicines in EMA's current report**, without company, category or status filters, including veterinary, withdrawn and refused medicines. Dedicated worker timer `optima-ema-medicines-daily.timer` captures the full report daily at **07:35 Europe/Madrid**, with a boot catch-up, 384 MiB memory and 20% CPU. Shared daily execution excludes this dedicated lane; historical execution is retained.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations" WHERE source_key = 'ema_medicines' GROUP BY source_key;`  
  Verified **160 raw-complete metadata observations / five raw batches**, including November 10 capture, query `c16271e6-6138-43eb-8260-7ee1c5d2360d`. **The complete current snapshot is already in curated Athena: 2,757 unique medicines, exactly matching all provider rows — 2,357 human and 400 veterinary.** Count query `6532bb35-9a44-497d-9f62-9ef42385f6bf`; category reconciliation `9aeddc8a-7839-46ec-b19a-63bc55530a30`. Remaining metadata labelling is separate from this complete current-snapshot publication. **43 focused tests passed.** Use `ema_medicines`, not the separate `uk_mhra` source. No new key is needed. This dataset does not contain every nationally authorised medicine across Europe; linked EPAR PDFs and past vintages remain separate. [Full-snapshot SQL, payload and runtime evidence](repair-notes/2026-11-10-ema-medicines/README.md).

- [x] **20. UK MHRA** (`uk_mhra`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=uk_mhra/`  
  Review: **Reviewed November 10, 2026 after original attachment-row validation, metadata replay and fresh PDF/text capture-to-Athena checks.**  
  Current collection state: **enabled — contract 2.0.3, reviewed-source date queues**, zero consecutive raw failures. Fixed the empty host contract and generic-content rejection with exact official CSV/XLSX row/composite identity checks. Expired orphan assertions remain separate; legacy unqualified IDs retain source provenance without being relabelled current. Requeued 51 unfinished jobs.  
  Scope: Existing ILAP/current/expired orphan lists **do not cover all drugs**. Added independently bounded capture of the **whole public MHRA product-information catalogue**, without company/product/document-type filters, retaining original PDFs, complete catalogue linkage and extracted text. Initial catalogue count **79,646 document entries**, later 79,648 as the feed changed; these are not unique-drug/licence counts or an assertion of exhaustive UK licence coverage. `optima-mhra-products.timer` continues after two minutes, up to ten entries/run, 384 MiB/20% CPU, with per-document timeout/gap logging. A failed document does not stop the following documents.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations" WHERE source_key = 'uk_mhra' GROUP BY source_key;`  
  Verified **70 raw-complete observations / four raw batches**, including November 10 product-document capture; query `24ec3092-38b7-483d-a2eb-6feb888be547`. New full document and **29,641 characters** verified in metadata (`0c7d8d98-1aeb-41df-ac6b-e0cb549f3d29`) and curated regulatory Athena (`e84f02ed-5f00-47ab-914c-dbf5f6d42d5f`). Initial ten-document batch had zero failures; the harvest continues and is **not complete**. **43 focused tests passed**, including failure isolation. No new credential is needed; use `uk_mhra`, not the selected `japan_pmda` source. Historical snapshots/current licence status and image-only PDF OCR remain separate checks. [Scope, SQL and live evidence](repair-notes/2026-11-10-mhra/README.md).

- [x] **21. Japan PMDA** (`japan_pmda`) — **designation-feed review passed; all-drug coverage still pending**  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=japan_pmda/`  
  Review: **Reviewed November 10, 2026 for the existing SAKIGAKE PDF, corrected table extraction and capture-to-Athena path. This does not mark all Japanese drugs covered.**  
  Current collection state: **enabled — contract 2.0.3, reviewed-source date queues**, zero consecutive raw failures. Fixed the empty allowed-host contract and added exact original PDF/table identity and field checks. Applicant and marketing-authorisation holder columns remain separate. Requeued 34 unfinished jobs; two incompatible flattened-text jobs were superseded only after verifying that the fresh typed batch covers every original ID and the identical provider PDF SHA-256. Raw history remains intact.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations" WHERE source_key = 'japan_pmda' GROUP BY source_key;`  
  Verified **50 raw-complete observations / two raw batches**, including today's **25-row full SAKIGAKE list**, query `e617fd63-1cc5-4c57-ab9c-39b509376863`. Fresh metadata product/applicant fields query `47b7eb0a-54b3-4a79-b26a-1fba83dbfefb`; curated readback `72bef4c6-b15c-4895-896d-3f5e0fff8362`. These are repeated designation observations, not 50 unique drugs. **39 focused tests passed.** New bounded worker capture runs daily at **07:45 Europe/Madrid**; historical designation-date scopes and metadata processing continue separately.  
  **Your access task — all drugs:** You confirmed November 10 that no Medi-Navi/My Drug List account exists. The documented all-prescription-drug package-insert export requires that registration. Start at [PMDA Medi-Navi](https://www.pmda.go.jp/safety/info-services/medi-navi/0006.html), then [My Drug List registration](https://push.info.pmda.go.jp/mypage/view/mypage/agreementForUse.html). After registration, use the all-package-insert download option, accept its terms and select **all package inserts**, PDF plus XML/SGML. Tell us when access/export is available; do not paste a password. Bulk ingestion and daily archive-update integration still require engineering verification. This route is prescription inserts, not an automatic claim of every OTC/veterinary product or historic versions. [Instructions, remaining scope and evidence](repair-notes/2026-11-10-pmda/README.md).

- [x] **22. Health Canada notices of compliance** (`canada_noc`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=canada_noc/`  
  Review: **Reviewed November 10, 2026 — original NOC responses, repaired metadata validation and verified capture-to-Athena path.**  
  Current collection state: **enabled, contract 2.0.3**, zero consecutive raw failures. Requeued 20 unfinished jobs; all four previously failed batches replayed successfully. Reviewed-source date queues isolate subsequent scope failures.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations" WHERE source_key = 'canada_noc' GROUP BY source_key;`  
  **The complete current notice snapshot is queryable in curated Athena: 38,276 unique notices**, exactly matching the official bulk response and all five product categories, including inactive records. Count query `7dbdee16-11e1-4731-a8d6-d4737451162a`. Initial metadata verification returned **192 raw-complete observations / six raw batches**, including fresh November 10 notice and product records; query `f9aec684-80da-4db1-9f21-7e7dce00381d`. Metadata backlog completion is separate from the complete curated notice snapshot. New full-notice daily timer: **07:55 Europe/Madrid**; historical date scopes remain enabled.  
  Added an all-NOC drug-product capture retaining **brand names, DINs and NOC linkage**, 4,000 rows per bounded continuation. **All 78,468 product records are now captured and verified in curated Athena**, query `f4b1aab3-e7a9-4601-8721-a503a70e4d07`; reconciliation found **zero missing notice links**, query `a6e1f156-2b60-4c20-b779-e25fc27d68e5`. These are notice/product records, not 78,468 distinct drugs. No company, drug-type or active-status filter is applied. `noc_crp_product_name` is a comparator/reference drug, not the actual brand name. This is all data returned by the NOC routes, not every marketed Canadian drug or past database vintages. **23 focused tests passed. No new API key/account is required.** Use us-east-1 / AwsDataCatalog / optima-collected-data, result reuse off. [Full snapshot SQL, product linkage, schedules and evidence](repair-notes/2026-11-10-canada-noc/README.md).

- [x] **23. Chinese Clinical Trial Registry** (`chictr`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=chictr/`  
  Review: **Reviewed November 10, 2026 — original rendered trial-detail pages, full parsed field lists and verified capture-to-Athena path.**  
  Current collection state: **enabled, contract 2.0.3**, zero consecutive raw failures. Added source-specific URL/project/registration/date/full-field validation and shared the capture parser. Requeued 23 unfinished jobs; all four original failed batches replayed successfully. Capture now retries incomplete table layouts before accepting trial details; per-source date queues isolate subsequent scope errors.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations" WHERE source_key = 'chictr' GROUP BY source_key;`  
  Rechecked and published six additional accepted batches: **94 raw-complete observations / 11 raw batches**, including today's 73-field trial detail. Uncached aggregate query `1eb865e0-79b2-49cd-89a2-18dcf8e42fcc`; metadata payload `8b40a008-6374-4e43-8c10-9f9c65deb31b`; regulatory readback `415b9fb0-304f-4136-8d63-baf1a41ea2fa`. Latest captured observation **2026-11-10 18:51:43 UTC**. Counts are observations, not unique/new trials or full historical coverage. Classified the remaining three website-discovery receipts as non-trial inputs and resolved their single open incident; all files and audit history remain. Real trial validation failures remain visible. **55 focused tests passed on recheck.**  
  Daily capture timer is enabled; the last run completed normally at its configured page limit (`partial`, not registry completion), with saved September catch-up windows still unfinished. Next scheduled run November 11 around **09:37 Europe/Madrid** at verification. Metadata worker/controller and 15 collection workers were running successfully; daily/historical controls are enabled. Historical public-discovery jobs are scheduled, but their receipts do not establish full trial-history coverage; older-window reconciliation remains separate. **No new access/key task for you.** Use us-east-1 / AwsDataCatalog / optima-collected-data, result reuse off. [Updated SQL, exact scope, schedules and recheck evidence](repair-notes/2026-11-10-chictr-recheck/README.md).

- [x] **24. NMPA trials** (`nmpa_trials`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=nmpa_trials/`  
  Review: **Reviewed November 10, 2026 — verified original inventory rows, full trial HTML/fields, supported events and capture-to-Athena path. Historical completeness remains in progress.**  
  Current collection state: **enabled, contract 2.0.3**, zero consecutive raw failures. Requeued 23 unfinished jobs; all four originally failed batches passed validation/replay (**80 inventory rows**). Inventory is explicitly labelled `registry_inventory` / `registry_inventory_not_trial_detail`; it is not promoted to a complete clinical-trial record. Full details require matching registration IDs, original fields and structured facts.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations" WHERE source_key = 'nmpa_trials' GROUP BY source_key;`  
  Verified **153 raw-complete observations / 14 raw batches**: **120 inventory rows, eight full trial snapshots and 25 events**, including new November 10 captures of historical-pending and current 2026 trials. Aggregate query `87886745-0c96-401b-ae66-80d8889aec94`; dataset/type breakdown `f175a369-12d1-4384-902c-35eca0f27458`; full metadata payload `cfb69beb-8c0a-44d8-89d8-cc7afe50a1f1`; regulatory Athena readback `b8d0c772-330b-4cbc-87a1-8756a34b6f3a`. Current samples retain **55–71 original fields**. These counts are observations, not the total unique registry or a completion claim.  
  Restored actual inventory/detail producers on **worker `i-06241bd1c4e91c2fc`**, preserving the original 6,359 completed trials and pending queue. Inventory continues five minutes after completion, details two minutes after completion; both bounded to 512 MiB/20% CPU. Daily discovery and historical continuation have independent attempts/cooldowns; bad trials cannot stop other trials. Shared request budget retains the existing 8,000 reserved slots/day. Old controller timers remain disabled intentionally. Baseline cursor advanced from 1,461 through 1,463; new daily IDs also produced verified full details. Metadata and verified publication queues continue. **79 focused tests passed. No access/key task for you.** [SQL samples, schedules, exact remaining scope and evidence](repair-notes/2026-11-10-nmpa-trials/README.md).

- [x] **25. PubMed abstracts** (`pubmed_abstracts`) — reviewed 10 November 2026  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=pubmed_abstracts/`  
  Fixed the incorrect article-full-text requirement. Contract **2.0.3** now verifies each complete original PubMed citation/abstract against the first-party EFetch XML, matching primary PMID, checksum, source URL and parsed fields. A genuinely absent abstract is flagged explicitly; it does not stop other records. Citation XML is retained; this source does not promise full articles. Legacy rows receive source-derived title/abstract context without changing their original evidence.  
  Metadata source **enabled**, zero consecutive raw failures. Requeued ten unfinished jobs; all four originally failed batches replayed successfully (**117 observations**). Your aggregate query now returns **179 raw-complete observations / eight raw batches**, including one live PMID probe and **61 observations from three fresh daily topic searches** (14 vaccine, 29 gene therapy, 18 immunotherapy). These are observations, not distinct papers or complete PubMed/archive coverage.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'pubmed_abstracts' GROUP BY source_key;`  
  Aggregate verified by query `4af823fd-99ad-42e1-8783-3618bdff2408`; latest ingestion **2026-11-10 20:03:30 UTC**. Actual title, citation XML and abstract sections read back in both metadata (`4c3804ac-8141-42b8-8752-548edc5d996c`) and specialist curated Athena (`c77edcf2-5e6c-48d5-9d3e-399870f6f43a`). All three daily windows have verified publication receipts.  
  Restored independent **worker** `optima-pubmed-daily.timer`: **08:10 Europe/Madrid**, with bounded hourly continuation, three configured topics and a seven-day publication-date lookback. Each topic has separate durable outcomes; maximum two pages/topic/run, 384 MiB and 20% CPU. Completed scopes reuse checkpoints. Shared daily lane excludes this source to avoid duplicate schedulers; historical source route is retained separately. Historical scheduler reports its configured work through October 26 drained, with coverage **not audited**; further archive/date-gap reconciliation and metadata catchup are separate from this pipeline review. **52 focused tests passed. No new key/account task for you.** [SQL samples, limits and repair evidence](repair-notes/2026-11-10-pubmed/README.md).

- [ ] **26. Europe PMC publication metadata** (`europe_pmc`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=europe_pmc/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:full_text`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:full_text` across 4 failed attempt(s).  
  Current raw processing: Archives provider metadata and versioned full text; extracts source identity, provenance, and publication metadata for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'europe_pmc' GROUP BY source_key;`

- [x] **27. Europe PMC full text** (`europe_pmc_fulltext`) — reviewed 10 November 2026  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=europe_pmc_fulltext/`  
  Fixed the contract's missing official **EBI / NCBI API hosts**. Contract **2.0.3** retains the full-text requirement and verifies the complete original JATS XML, primary PMCID, checksum, article title/body and source URL; abstract-only, altered or mismatched articles fail. Original XML and source licence statements remain saved. New records expose parsed title, full body text, identifiers and dates in both metadata and curated payloads.  
  Source **enabled**, zero consecutive raw failures. All three originally failed article batches replayed successfully. Requeued **71 unfinished metadata jobs**; confirmed website-discovery receipts are classified as non-article inputs and cannot recur as missing-full-text errors. Their audit records and all raw files remain retained. Your aggregate SQL now returns **14 raw-complete observations / 14 raw batches**, including fresh current articles and a successful original January 2021 historical scope. Counts are observations and include repeated article captures; they are not unique papers or full-history completion.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'europe_pmc_fulltext' GROUP BY source_key;`  
  Verified aggregate query `882b0e2c-ab5e-4915-9edb-fbbac8131f59`; latest verified ingestion **2026-11-10 20:21:14 UTC**. Payload readback: metadata `59c70fd6-2148-42d1-bc41-fde1f8cfa162`, curated specialist table `46949f31-b5f8-44cc-aee9-d3c972b72e9c`. Fresh samples have matching titles, **105,626–210,043 XML characters** and **37,923–72,032 body-text characters** in both tables. Eleven captured article windows have verified curated publication receipts.  
  Restored worker timers **`optima-epmc-fulltext-discover.timer`** and **`optima-epmc-fulltext-capture.timer`**, continuing two minutes after completion. Daily searches use the three configured clinical-trial topics with a seven-day lookback; shared historical discovery queues are indexed 50 entries each per run, retaining cursors. Article capture attempts at most four documents/run, with a 75-second per-article deadline and six-hour failure cooldown. Each service is bounded to 384 MiB / 20% CPU. Recovered **20 original saved article scopes** into the queue; historical indexing/capture/publication continue. Latest discovery and capture runs succeeded; metadata and other workers remain active. **59 focused tests passed. No new API key/account task for you.** [SQL samples, scope limits and evidence](repair-notes/2026-11-10-europe-pmc-fulltext/README.md).

- [x] **28. Crossref conference proceedings** (`crossref_proceedings`) — reviewed 10 November 2026, **DOI metadata scope**  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=crossref_proceedings/`  
  Fixed the incorrect publisher-full-text requirement. Contract **2.0.3** verifies complete original Crossref proceedings-article metadata, checksummed API response, DOI/type/source URL and every returned field. Unprovided abstracts and missing publisher papers are explicitly flagged; metadata is not classified as a full paper. Existing separately archived API pages now expand into their real DOI records. All original data and rights fields remain retained.  
  Metadata source **enabled**, zero consecutive raw failures. Requeued **297 unfinished jobs**; all four originally failed batches replayed successfully (**128 observations**). Fresh uncached aggregate now returns **321 raw-complete observations / 11 linked batches**, including a live DOI response captured **2026-11-10 20:43:51 UTC**. Observations may repeat a DOI; these are not archive/unique-paper completion counts.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'crossref_proceedings' GROUP BY source_key;`  
  Aggregate query `62e7f35d-3c00-4309-8a82-9ee83c850343`; fresh metadata payload `51a53236-a504-4c58-be82-713062394a20`; conference curated payload `e6d2e524-95c6-4df2-a926-8aef7e7e80af`. Matching DOI, title, publisher, work type and publication date were inspected in both tables. Curated table is **`optima_conference_research.conference_observations_windows`**, with full provider fields in `data_json`.  
  Restored independent worker **`optima-crossref-resumed.timer`** for daily/history capture and controller **`optima-crossref-publication-resumed.timer`** for bounded publication, both continuing two minutes after completion. Preserved original universe/checkpoints, including the old 2021-origin archive cursor. The 2016 target is separate; its large first window progressed **12,000 → 24,000 → 36,000 → 48,000 saved records** with actual cursor continuation, and remains partial pending source exhaustion. Daily cursor is caught up through November 9. Old controller jobs were confirmed waiting, then disabled in favor of these replacements; monitoring records the migration. **43 focused tests passed. No new key/account task for you.** [SQL checks, exact limits, full-text gap and evidence](repair-notes/2026-11-10-crossref/README.md).

- [x] **29. CMS coverage policies** (`cms_coverage`) — reviewed 10 November 2026  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=cms_coverage/`  
  Repaired the generic JSON validator that stopped valid CMS responses. Contract **2.0.3** checks checksum, original response, document/version identity and complete returned fields. Both metadata sources are **enabled**, zero consecutive raw failures; original failed batches replayed. Documentation web pages remain discovery evidence and cannot stop the document route.  
  Uncached Athena proof: **114 observations / 6 linked raw batches**, all raw-complete, including fresh November 10 ingestion. Policy rows are inventory records; full coverage text is in the companion document source.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'cms_coverage' GROUP BY source_key;`  
  Live provider → raw S3 → metadata → Athena checks passed; fresh native records also verified in `optima_specialist_inputs.source_observations_windows`. Independent CMS discovery, document capture and publication timers continue every two minutes after completion; new batches enter the metadata queue directly. Daily refresh and historical annual/version discovery continue. **61 tests passed. No key/account/restart task for you.** Reviewed scope is national Medicare NCD data; all-history completion, local/commercial payers, entity links and past API vintages remain separate. [Evidence and SQL samples](repair-notes/2026-11-10-cms/README.md).

- [x] **30. CMS coverage documents** (`cms_coverage_documents`) — reviewed 10 November 2026  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=cms_coverage_documents/`  
  Repaired the generic JSON validator that stopped valid CMS responses. Contract **2.0.3** checks checksum, original response, document/version identity and complete returned fields. Both metadata sources are **enabled**, zero consecutive raw failures; original failed batches replayed. Documentation web pages remain discovery evidence and cannot stop the document route.  
  Uncached Athena proof: **8 observations / 8 linked raw batches**, all raw-complete, including fresh November 10 ingestion. Original coverage text and all provider fields are retained; readable criteria, revision history, benefit category and supplied dates are in `labelled_json` → `$.payload.cms_context`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'cms_coverage_documents' GROUP BY source_key;`  
  Live provider → raw S3 → metadata → Athena checks passed; fresh native records also verified in `optima_specialist_inputs.source_observations_windows`. Independent CMS discovery, document capture and publication timers continue every two minutes after completion; new batches enter the metadata queue directly. Daily refresh and historical annual/version discovery continue. **61 tests passed. No key/account/restart task for you.** Reviewed scope is national Medicare NCD data; all-history completion, local/commercial payers, entity links and past API vintages remain separate. [Evidence and SQL samples](repair-notes/2026-11-10-cms/README.md).

### Day 3 — Wednesday — 11 November 2026 (15 catalog entries)

- [x] **31. CMS payments catalog and financial records** (`cms_payments_catalog`) — reviewed 11 November 2026  
  Catalog raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/cms_payments_catalog/`. One unchanged provider JSON catalog can describe many datasets and repeat publisher/contact fields; it is not the payment data. Actual originals: `s3://data-collection-059416028963-us-east-1-an/research-data/cms-financial/files/<edition_id>/original.csv`.  
  Repaired metadata validation with contract **2.0.3**: exact original descriptor/checksum, dataset identity, official publisher and download links. All four failed batches replayed. Catalog source **enabled**, zero consecutive raw failures. Fresh November 11 capture: **40 dataset IDs**; metadata now returns **168 raw-complete observations / 5 linked batches** (repeated observations across capture dates, not 168 different datasets).  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'cms_payments_catalog' GROUP BY source_key;`  
  **Actual financial data is in different tables:** `optima_collected_data.cms_open_payments_rows` has **76,013,225 rows / 15 editions**; `optima_collected_data.cms_drug_spending_rows` has **63,336 rows / 5 editions**. Complete provider fields are retained in `row_json`; edition/raw-file provenance is in `optima_collected_data.cms_financial_editions`. Checked actual general/research/ownership/spending payloads, not just table counts.  
  Financial Athena checks: `SELECT count(*) FROM optima_collected_data.cms_open_payments_rows;` and `SELECT count(*) FROM optima_collected_data.cms_drug_spending_rows;`. For file scope and original links: `SELECT source,title,program_year,category,row_count,edition_id,raw_key,sha256 FROM optima_collected_data.cms_financial_editions ORDER BY source,program_year,category;`.  
  Restored daily discovery and file continuation from the verified 20-file checkpoint. At **15:25 Madrid time on November 11**, the automatic job reconciled every edition's Athena count with its committed CSV checkpoint and verified raw sizes/checksum receipts. CMS controller jobs now have an independent **384 MiB** budget; catalog capture remains on the worker. Both timers and catalog publication are enabled; metadata worker/all 15 historical workers checked active. **67 tests passed. No key/account/manual restart action for you.** Configured 2021–2025 payments and five current spending editions are complete; this is not every prior release, all-payer claims, historical vintages or verified constellation entity links. [Evidence and bounded 20-row financial SQL samples](repair-notes/2026-11-11-cms-payments/README.md).

- [x] **32. FDA Dashboard compliance actions** (`fda_dd_compliance_actions`) — reviewed 11 November 2026  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=fda_dd_compliance_actions/`; original API responses linked under `source_documents/fda_dd_compliance_actions/`.  
  Repaired source-specific metadata validation under contract **2.0.3**. Source **enabled**, zero consecutive raw failures. Verified **162 raw-complete observations / 6 linked batches** in Athena, including fresh November 11 ingestion. Observations include repeated capture dates; this is not an archive-completion or unique-event count.  
  Retains action type/date, CaseInjunctionID, FEI, firm, center and all returned fields; original warning-letter documents and resolved company links remain separate.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'fda_dd_compliance_actions' GROUP BY source_key;`  
  Fresh API → raw S3 → metadata → both Athena destinations verified: **2 records** in the bounded verification window. Inspected actual provider fields and source context. Daily capture, independent historical routes where applicable, metadata continuation and publication remain scheduled; older backlog continues. **66 tests passed. No API-key/account/manual restart action for you.** [Evidence, exact scope and 20-row SQL checks](repair-notes/2026-11-11-fda-authenticated/README.md).

- [x] **33. FDA Dashboard import refusals** (`fda_dd_import_refusals`) — reviewed 11 November 2026  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=fda_dd_import_refusals/`; original API responses linked under `source_documents/fda_dd_import_refusals/`.  
  Repaired source-specific metadata validation under contract **2.0.3**. Source **enabled**, zero consecutive raw failures. Verified **425 raw-complete observations / 8 linked batches** in Athena, including fresh November 11 ingestion. Observations include repeated capture dates; this is not an archive-completion or unique-event count.  
  Retains shipment/product codes and descriptions, refusal dates/charges, FEI/firm and country fields; all returned fields and code strings preserved.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'fda_dd_import_refusals' GROUP BY source_key;`  
  Fresh API → raw S3 → metadata → both Athena destinations verified: **265 records** in the bounded verification window. Inspected actual provider fields and source context. Daily capture, independent historical routes where applicable, metadata continuation and publication remain scheduled; older backlog continues. **66 tests passed. No API-key/account/manual restart action for you.** [Evidence, exact scope and 20-row SQL checks](repair-notes/2026-11-11-fda-authenticated/README.md).

- [x] **34. FDA Dashboard inspection citations** (`fda_dd_inspections_citations`) — reviewed 11 November 2026  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=fda_dd_inspections_citations/`; original API responses linked under `source_documents/fda_dd_inspections_citations/`.  
  Repaired source-specific metadata validation under contract **2.0.3**. Source **enabled**, zero consecutive raw failures. Verified **195 raw-complete observations / 6 linked batches** in Athena, including fresh November 11 ingestion. Observations include repeated capture dates; this is not an archive-completion or unique-event count.  
  Retains inspection + citation identities, CFR reference, long/short descriptions, FEI/firm and inspection dates; this API dataset does not include original 483 documents.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'fda_dd_inspections_citations' GROUP BY source_key;`  
  Fresh API → raw S3 → metadata → both Athena destinations verified: **35 records** in the bounded verification window. Inspected actual provider fields and source context. Daily capture, independent historical routes where applicable, metadata continuation and publication remain scheduled; older backlog continues. **66 tests passed. No API-key/account/manual restart action for you.** [Evidence, exact scope and 20-row SQL checks](repair-notes/2026-11-11-fda-authenticated/README.md).

- [ ] **35. FDA Dashboard inspection classifications** (`fda_dd_inspections_classifications`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=fda_dd_inspections_classifications/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'fda_dd_inspections_classifications' GROUP BY source_key;`

- [x] **36. FDA Enforcement Report recalls** (`fda_ires_recalls`) — reviewed 11 November 2026  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=fda_ires_recalls/`; original API responses linked under `source_documents/fda_ires_recalls/`.  
  Repaired source-specific metadata validation under contract **2.0.3**. Source **enabled**, zero consecutive raw failures. Verified **179 raw-complete observations / 4 linked batches** in Athena, including fresh November 11 ingestion. Observations include repeated capture dates; this is not an archive-completion or unique-event count.  
  Retains the configured eleven recall columns plus server RID, including product/recall IDs, firm, description/reason, classification and dates. Explicit selected-column flag; selected by event modification date, not recall initiation or full case-file history.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'fda_ires_recalls' GROUP BY source_key;`  
  Fresh API → raw S3 → metadata → both Athena destinations verified: **51 records** in the bounded verification window. Inspected actual provider fields and source context. Daily capture, independent historical routes where applicable, metadata continuation and publication remain scheduled; older backlog continues. **66 tests passed. No API-key/account/manual restart action for you.** [Evidence, exact scope and 20-row SQL checks](repair-notes/2026-11-11-fda-authenticated/README.md).

- [x] **37. FDA product codes** (`fda_product_codes`) — reviewed 11 November 2026  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=fda_product_codes/`; original API responses linked under `source_documents/fda_product_codes/`.  
  Repaired source-specific metadata validation under contract **2.0.3**. Source **enabled**, zero consecutive raw failures. Verified **217 raw-complete observations / 4 linked batches** in Athena, including fresh November 11 ingestion. Observations include repeated capture dates; this is not an archive-completion or unique-event count.  
  Reviewed **current industry reference only**: all 89 industry IDs/descriptions, preserving leading zeroes. It is not the full five-component code hierarchy, all seven-character codes or historical code vintages.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'fda_product_codes' GROUP BY source_key;`  
  Fresh API → raw S3 → metadata → both Athena destinations verified: **89 records** in the bounded verification window. Inspected actual provider fields and source context. Daily capture, independent historical routes where applicable, metadata continuation and publication remain scheduled; older backlog continues. **66 tests passed. No API-key/account/manual restart action for you.** [Evidence, exact scope and 20-row SQL checks](repair-notes/2026-11-11-fda-authenticated/README.md).

- [x] **38. NIH RePORTER grants** (`nih_reporter`) — reviewed 11 November 2026, scoped pipeline verification  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=nih_reporter/`; checksummed originals linked in each record.  
  Repaired source-specific raw validation and Athena publication. Verified snapshot: **2830 observations / 46 linked collection batches**, all 2830 raw-complete for the declared dataset. These are row occurrences, not unique-event or historical-completion counts.  
  Complete returned NIH project-application records: grant IDs, project numbers, title/abstract, amount, organisation and investigators. Configured topics/organisation candidates; grant proposals and historical API vintages remain separate. One October 9 batch lacks its commit checkpoint and remains uncommitted, with raw files retained.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'nih_reporter' GROUP BY source_key;`    
  Daily/historical capture where applicable, metadata and publication continuations verified. **68 tests passed. No new key/account/manual restart action for you.** [Evidence, limitations and bounded sample queries](repair-notes/2026-11-11-grants-patents-procurement/README.md).

- [x] **39. Google Patents BigQuery** (`google_patents_bigquery`) — reviewed 11 November 2026, scoped pipeline verification  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=google_patents_bigquery/`; checksummed originals linked in each record.  
  Repaired source-specific raw validation and Athena publication. Verified snapshot: **2608 observations / 11 linked collection batches**, all 2608 raw-complete for the declared dataset. These are row occurrences, not unique-event or historical-completion counts.  
  Verified bibliographic exports, original completed BigQuery result pages, provider identifiers and typed schema. Patent claims/specification/full text remain uncollected by this route; this review covers the bibliographic pipeline only.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'google_patents_bigquery' GROUP BY source_key;`    
  Daily/historical capture where applicable, metadata and publication continuations verified. **68 tests passed. No new key/account/manual restart action for you.** [Evidence, limitations and bounded sample queries](repair-notes/2026-11-11-grants-patents-procurement/README.md).

- [x] **40. USPTO Open Data Portal** (`uspto_odp`) — reviewed 11 November 2026, scoped pipeline verification  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=uspto_odp/`; checksummed originals linked in each record.  
  Repaired source-specific raw validation and Athena publication. Verified snapshot: **1859 observations / 60 linked collection batches**, all 1859 raw-complete for the declared dataset. These are row occurrences, not unique-event or historical-completion counts.  
  Verified application bibliography, normalized assignment ledgers, office-action text with original PDFs, and petition-decision PDFs, separately by dataset. Candidate entity links and current legal title remain unverified. Approved application/document exclusions are retained and excluded from full-document observations.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'uspto_odp' GROUP BY source_key;`    
  Daily/historical capture where applicable, metadata and publication continuations verified. **68 tests passed. No new key/account/manual restart action for you.** [Evidence, limitations and bounded sample queries](repair-notes/2026-11-11-grants-patents-procurement/README.md).

- [x] **41. USPTO assignment histories** (`uspto_assignment_histories`) — reviewed 11 November 2026, scoped pipeline verification  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=uspto_assignment_histories/`; checksummed originals linked in each record.  
  Repaired source-specific raw validation and Athena publication. Verified snapshot: **131 observations / 60 linked collection batches**, all 131 raw-complete for the declared dataset. These are row occurrences, not unique-event or historical-completion counts.  
  Recorded assignment events and the complete returned chain for the eight configured applications. Recorded deed images, all USPTO assignments and legal/current ownership are separate coverage requirements.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'uspto_assignment_histories' GROUP BY source_key;`    
  Daily/historical capture where applicable, metadata and publication continuations verified. **68 tests passed. No new key/account/manual restart action for you.** [Evidence, limitations and bounded sample queries](repair-notes/2026-11-11-grants-patents-procurement/README.md).

- [x] **42. Tenders Electronic Daily procurement notices** (`ted_notices`) — reviewed 11 November 2026, scoped pipeline verification  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=ted_notices/`; checksummed originals linked in each record.  
  Repaired source-specific raw validation and Athena publication. Verified snapshot: **2323 observations / 77 linked collection batches**, all 2323 raw-complete for the declared dataset. These are row occurrences, not unique-event or historical-completion counts.  
  Original notice XML, complete parsed XML trees and provider search metadata for configured CPV scopes. Oversized notices retain ordered content chunks; chunks are not additional notices or awards. The fresh verified notice is 768246-2026. XML retrieval gaps remain separately retryable.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'ted_notices' GROUP BY source_key;`    
  Daily/historical capture where applicable, metadata and publication continuations verified. **68 tests passed. No new key/account/manual restart action for you.** [Evidence, limitations and bounded sample queries](repair-notes/2026-11-11-grants-patents-procurement/README.md).

- [x] **43. USAspending federal awards** (`usa_spending`) — reviewed 11 November 2026, scoped pipeline verification  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=usa_spending/`; checksummed originals linked in each record.  
  Repaired source-specific raw validation and Athena publication. Verified snapshot: **1703 observations / 83 linked collection batches**, all 1703 raw-complete for the declared dataset. These are row occurrences, not unique-event or historical-completion counts.  
  Complete returned selected award-summary fields for named-universe contract candidates. Grant/loan programmes, all recipients, full transactions and full award dossiers are outside this configured route.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'usa_spending' GROUP BY source_key;`    
  Daily/historical capture where applicable, metadata and publication continuations verified. **68 tests passed. No new key/account/manual restart action for you.** [Evidence, limitations and bounded sample queries](repair-notes/2026-11-11-grants-patents-procurement/README.md).

- [ ] **44. GitHub repositories and SDKs (paused)** (`github_sdk`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=github_sdk/`  
  Current collection state: **owner_paused** — deliberate pause, not a raw-validation stop  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'github_sdk' GROUP BY source_key;`

- [x] **45. NIST robotics methods** (`nist_robotics_methods`) — reviewed 11 November 2026, scoped pipeline verification  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=nist_robotics_methods/`; checksummed originals linked in each record.  
  Repaired source-specific raw validation and Athena publication. Verified snapshot: **130 observations / 130 linked collection batches**, all 130 raw-complete for the declared dataset. These are row occurrences, not unique-event or historical-completion counts.  
  Original NIST robotics pages and a fresh 19-page grasp-performance study PDF with 6,713 extracted text characters. Discovery/project/method/PDF kinds remain explicit. Companion documents use nist_robotics_documents. Graphics, measurements not present in extracted text and historical website vintages are not inferred.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'nist_robotics_methods' GROUP BY source_key;`    
  Daily/historical capture where applicable, metadata and publication continuations verified. **68 tests passed. No new key/account/manual restart action for you.** [Evidence, limitations and bounded sample queries](repair-notes/2026-11-11-grants-patents-procurement/README.md).

### Day 4 — Thursday — 12 November 2026 (15 catalog entries)

- [ ] **46. MLPerf benchmark results** (`mlperf_results`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=mlperf_results/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'mlperf_results' GROUP BY source_key;`

- [ ] **47. CPSC recalls** (`cpsc_recalls`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=cpsc_recalls/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'cpsc_recalls' GROUP BY source_key;`

- [ ] **48. Federal Register** (`federal_register`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=federal_register/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'federal_register' GROUP BY source_key;`

- [ ] **49. Trade screening lists** (`trade_screening`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=trade_screening/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'trade_screening' GROUP BY source_key;`

- [ ] **50. USGS minerals** (`usgs_minerals`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=usgs_minerals/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` (latest live failure only).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'usgs_minerals' GROUP BY source_key;`

- [ ] **51. UN Comtrade** (`un_comtrade`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=un_comtrade/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` across 4 failed attempt(s).  
  Current raw processing: Archives native observations with dimensions, units, flags, and timestamps; extracts normalized measurements for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'un_comtrade' GROUP BY source_key;`

- [ ] **52. Department of Energy storage program** (`doe_storage_program`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=doe_storage_program/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'doe_storage_program' GROUP BY source_key;`

- [ ] **53. EIA battery generators** (`eia_battery_generators`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=eia_battery_generators/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'eia_battery_generators' GROUP BY source_key;`

- [ ] **54. EIA generator index** (`eia_generator_index`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=eia_generator_index/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record`; `public_capture_is_discovery_page_only` across 7 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'eia_generator_index' GROUP BY source_key;`

- [ ] **55. EIA retail prices** (`eia_retail_prices`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=eia_retail_prices/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives native observations with dimensions, units, flags, and timestamps; extracts normalized measurements for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'eia_retail_prices' GROUP BY source_key;`

- [ ] **56. California ISO prices** (`caiso_prices`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=caiso_prices/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives native observations with dimensions, units, flags, and timestamps; extracts normalized measurements for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'caiso_prices' GROUP BY source_key;`

- [ ] **57. BLS wages** (`bls_wages`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=bls_wages/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives native observations with dimensions, units, flags, and timestamps; extracts normalized measurements for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'bls_wages' GROUP BY source_key;`

- [ ] **58. Research Organization Registry institutions** (`ror_institutions`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=ror_institutions/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'ror_institutions' GROUP BY source_key;`

- [ ] **59. Reddit posts and comments (paused)** (`reddit`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=reddit/`  
  Current collection state: **owner_paused** — deliberate pause, not a raw-validation stop  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `optima_social_research.reddit_records`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'reddit' GROUP BY source_key;`

- [ ] **60. DataForSEO search capture** (`S65`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=S65/`  
  Current collection state: **access_layer** — routing/access service, not an independently collected raw dataset  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `optima_source_readiness.source_samples_windows`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'S65' GROUP BY source_key;`

### Day 5 — Friday — 13 November 2026 (15 catalog entries)

- [ ] **61. Bluesky posts (paused)** (`bluesky_search`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=bluesky_search/`  
  Current collection state: **owner_paused** — deliberate pause, not a raw-validation stop  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `social_records`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'bluesky_search' GROUP BY source_key;`

- [ ] **62. SAM.gov opportunities** (`sam_gov_opportunities`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=sam_gov_opportunities/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'sam_gov_opportunities' GROUP BY source_key;`

- [ ] **63. USPTO Office Actions** (`uspto_odp`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=uspto_odp/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:patent_document`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:patent_document` across 4 failed attempt(s).  
  Current raw processing: Archives the provider patent record plus patent document; extracts patent identity, provenance, and normalized source-record fields for `patent_office_actions`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'uspto_odp' GROUP BY source_key;`

- [ ] **64. USPTO final Petition Decisions** (`uspto_odp`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=uspto_odp/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:patent_document`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:patent_document` across 4 failed attempt(s).  
  Current raw processing: Archives the provider patent record plus patent document; extracts patent identity, provenance, and normalized source-record fields for `patent_petition_decisions`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'uspto_odp' GROUP BY source_key;`

- [ ] **65. BIS SDMX API** (`bis_sdmx_api`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=bis_sdmx_api/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives native observations with dimensions, units, flags, and timestamps; extracts normalized measurements for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'bis_sdmx_api' GROUP BY source_key;`

- [ ] **66. FRED / ALFRED series and vintages** (`fred_alfred_series_and_vintages`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=fred_alfred_series_and_vintages/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives native observations with dimensions, units, flags, and timestamps; extracts normalized measurements for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'fred_alfred_series_and_vintages' GROUP BY source_key;`

- [ ] **67. UNIDO IIP and INDSTAT** (`unido_iip_and_indstat`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=unido_iip_and_indstat/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'unido_iip_and_indstat' GROUP BY source_key;`

- [ ] **68. ILOSTAT labor statistics** (`ilostat_labor_statistics`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=ilostat_labor_statistics/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'ilostat_labor_statistics' GROUP BY source_key;`

- [ ] **69. IMF PortWatch shipping activity** (`imf_portwatch_shipping_activity`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=imf_portwatch_shipping_activity/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'imf_portwatch_shipping_activity' GROUP BY source_key;`

- [ ] **70. Ember electricity demand and generation** (`ember_electricity_demand_and_generation`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=ember_electricity_demand_and_generation/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` across 20 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'ember_electricity_demand_and_generation' GROUP BY source_key;`

- [ ] **71. WTO Timeseries API** (`wto_timeseries_api`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=wto_timeseries_api/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives native observations with dimensions, units, flags, and timestamps; extracts normalized measurements for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'wto_timeseries_api' GROUP BY source_key;`

- [ ] **72. WTO Quantitative Restrictions API** (`wto_quantitative_restrictions_api`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=wto_quantitative_restrictions_api/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'wto_quantitative_restrictions_api' GROUP BY source_key;`

- [ ] **73. WTO ePing SPS/TBT notifications** (`wto_eping_sps_tbt_notifications`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=wto_eping_sps_tbt_notifications/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'wto_eping_sps_tbt_notifications' GROUP BY source_key;`

- [ ] **74. EPO OPS patent legal events** (`epo_ops_patent_legal_events`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=epo_ops_patent_legal_events/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'epo_ops_patent_legal_events' GROUP BY source_key;`

- [ ] **75. Copernicus ERA5 / ERA5-Land** (`copernicus_era5_era5_land`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=copernicus_era5_era5_land/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'copernicus_era5_era5_land' GROUP BY source_key;`

### Day 6 — Monday — 16 November 2026 (15 catalog entries)

- [ ] **76. NASA POWER weather and solar resource** (`nasa_power_weather_and_solar_resource`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=nasa_power_weather_and_solar_resource/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives native observations with dimensions, units, flags, and timestamps; extracts normalized measurements for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'nasa_power_weather_and_solar_resource' GROUP BY source_key;`

- [ ] **77. USGS Earthquake Catalog API** (`usgs_earthquakes`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=usgs_earthquakes/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'usgs_earthquakes' GROUP BY source_key;`

- [ ] **78. UCDP organized violence** (`ucdp_organized_violence`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=ucdp_organized_violence/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'ucdp_organized_violence' GROUP BY source_key;`

- [ ] **79. arXiv early technical disclosures** (`arxiv`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=arxiv/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:full_text`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:full_text` across 4 failed attempt(s).  
  Current raw processing: Archives provider metadata and versioned full text; extracts source identity, provenance, and publication metadata for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'arxiv' GROUP BY source_key;`

- [ ] **80. England NHSBSA prescribing data** (`england_nhsbsa_prescribing_data`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=england_nhsbsa_prescribing_data/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` across 1 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'england_nhsbsa_prescribing_data' GROUP BY source_key;`

- [ ] **81. Decodo shared web retrieval (access layer)** (`decodo_shared_web_retrieval_access_layer`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=decodo_shared_web_retrieval_access_layer/`  
  Current collection state: **access_layer** — routing/access service, not an independently collected raw dataset  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'decodo_shared_web_retrieval_access_layer' GROUP BY source_key;`

- [ ] **82. SIA / WSTS public semiconductor sales** (`sia_wsts_public_semiconductor_sales`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=sia_wsts_public_semiconductor_sales/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 6 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'sia_wsts_public_semiconductor_sales' GROUP BY source_key;`

- [ ] **83. SEMI worldwide equipment billings** (`semi_worldwide_equipment_billings`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=semi_worldwide_equipment_billings/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'semi_worldwide_equipment_billings' GROUP BY source_key;`

- [ ] **84. International Federation of Robotics World Robotics** (`international_federation_of_robotics_world_robotics`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=international_federation_of_robotics_world_robotics/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record`; `public_capture_is_discovery_page_only` across 18 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'international_federation_of_robotics_world_robotics' GROUP BY source_key;`

- [ ] **85. IEA-PVPS solar deployment reports** (`iea_pvps_solar_deployment_reports`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=iea_pvps_solar_deployment_reports/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 10 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'iea_pvps_solar_deployment_reports' GROUP BY source_key;`

- [ ] **86. Germany G-BA drug benefit assessments** (`germany_g_ba_drug_benefit_assessments`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=germany_g_ba_drug_benefit_assessments/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'germany_g_ba_drug_benefit_assessments' GROUP BY source_key;`

- [ ] **87. France HAS medicine assessment opinions** (`france_has_medicine_assessment_opinions`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=france_has_medicine_assessment_opinions/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'france_has_medicine_assessment_opinions' GROUP BY source_key;`

- [ ] **88. NICE technology appraisals** (`nice_technology_appraisals`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=nice_technology_appraisals/`  
  Current collection state: **owner_paused** — deliberate pause, not a raw-validation stop  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'nice_technology_appraisals' GROUP BY source_key;`

- [ ] **89. Canada CDA-AMC / CADTH reimbursement reviews** (`canada_cda_amc_cadth_reimbursement_reviews`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=canada_cda_amc_cadth_reimbursement_reviews/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'canada_cda_amc_cadth_reimbursement_reviews' GROUP BY source_key;`

- [ ] **90. France Assurance Maladie Open Medic** (`france_assurance_maladie_open_medic`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=france_assurance_maladie_open_medic/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'france_assurance_maladie_open_medic' GROUP BY source_key;`

### Day 7 — Tuesday — 17 November 2026 (15 catalog entries)

- [ ] **91. Japan MHLW NDB Open Data** (`japan_mhlw_ndb_open_data`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=japan_mhlw_ndb_open_data/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'japan_mhlw_ndb_open_data' GROUP BY source_key;`

- [ ] **92. CNINFO mainland-China company disclosures** (`cninfo_mainland_china_company_disclosures`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=cninfo_mainland_china_company_disclosures/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives the provider filing record plus original primary document; extracts filing identity, provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'cninfo_mainland_china_company_disclosures' GROUP BY source_key;`

- [ ] **93. China NBS industrial production** (`china_nbs_industrial_production`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=china_nbs_industrial_production/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'china_nbs_industrial_production' GROUP BY source_key;`

- [ ] **94. China MIIT electronics and battery statistics** (`china_miit_electronics_and_battery_statistics`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=china_miit_electronics_and_battery_statistics/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'china_miit_electronics_and_battery_statistics' GROUP BY source_key;`

- [ ] **95. China NEA power statistics** (`china_nea_power_statistics`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=china_nea_power_statistics/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 5 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'china_nea_power_statistics' GROUP BY source_key;`

- [ ] **96. China NHSA reimbursement and procurement** (`china_nhsa_reimbursement_and_procurement`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=china_nhsa_reimbursement_and_procurement/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'china_nhsa_reimbursement_and_procurement' GROUP BY source_key;`

- [ ] **97. China MOFCOM export controls** (`china_mofcom_export_controls`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=china_mofcom_export_controls/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'china_mofcom_export_controls' GROUP BY source_key;`

- [ ] **98. South Korea FSS OpenDART** (`south_korea_fss_opendart`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=south_korea_fss_opendart/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:primary_document`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:primary_document` across 4 failed attempt(s).  
  Current raw processing: Archives the provider filing record plus original primary document; extracts filing identity, provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'south_korea_fss_opendart' GROUP BY source_key;`

- [ ] **99. South Korea KOSIS statistical OpenAPI** (`south_korea_kosis_statistical_openapi`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=south_korea_kosis_statistical_openapi/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'south_korea_kosis_statistical_openapi' GROUP BY source_key;`

- [ ] **100. Taiwan TWSE/MOPS issuer and revenue archives** (`taiwan_twse_mops_issuer_and_revenue_archives`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=taiwan_twse_mops_issuer_and_revenue_archives/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:primary_document`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:primary_document` across 2 failed attempt(s).  
  Current raw processing: Archives the provider filing record plus original primary document; extracts filing identity, provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'taiwan_twse_mops_issuer_and_revenue_archives' GROUP BY source_key;`

- [ ] **101. Taiwan customs trade statistics** (`taiwan_customs_trade_statistics`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=taiwan_customs_trade_statistics/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'taiwan_customs_trade_statistics' GROUP BY source_key;`

- [ ] **102. India IBM mineral production** (`india_ibm_mineral_production`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=india_ibm_mineral_production/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'india_ibm_mineral_production' GROUP BY source_key;`

- [ ] **103. Indonesia ESDM and Geological Agency mineral statistics** (`indonesia_esdm_and_geological_agency_mineral_statistics`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=indonesia_esdm_and_geological_agency_mineral_statistics/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record`; `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'indonesia_esdm_and_geological_agency_mineral_statistics' GROUP BY source_key;`

- [ ] **104. Brazil ANM mineral yearbook** (`brazil_anm_mineral_yearbook`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=brazil_anm_mineral_yearbook/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'brazil_anm_mineral_yearbook' GROUP BY source_key;`

- [ ] **105. Brazil ANM CFEM mining royalties** (`brazil_anm_cfem_mining_royalties`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=brazil_anm_cfem_mining_royalties/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'brazil_anm_cfem_mining_royalties' GROUP BY source_key;`

### Day 8 — Wednesday — 18 November 2026 (15 catalog entries)

- [ ] **106. Brazil MDIC Comex Stat API** (`brazil_mdic_comex_stat_api`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=brazil_mdic_comex_stat_api/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'brazil_mdic_comex_stat_api' GROUP BY source_key;`

- [ ] **107. Chile COCHILCO production and mining economics** (`chile_cochilco_production_and_mining_economics`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=chile_cochilco_production_and_mining_economics/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'chile_cochilco_production_and_mining_economics' GROUP BY source_key;`

- [ ] **108. Chile SERNAGEOMIN mining yearbooks** (`chile_sernageomin_mining_yearbooks`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=chile_sernageomin_mining_yearbooks/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'chile_sernageomin_mining_yearbooks' GROUP BY source_key;`

- [ ] **109. Chile SMA SNIFA environmental compliance** (`chile_sma_snifa_environmental_compliance`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=chile_sma_snifa_environmental_compliance/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'chile_sma_snifa_environmental_compliance' GROUP BY source_key;`

- [ ] **110. Peru MINEM mining bulletins and yearbooks** (`peru_minem_mining_bulletins_and_yearbooks`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=peru_minem_mining_bulletins_and_yearbooks/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'peru_minem_mining_bulletins_and_yearbooks' GROUP BY source_key;`

- [ ] **111. Argentina SIACAM mining indicators** (`argentina_siacam_mining_indicators`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=argentina_siacam_mining_indicators/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'argentina_siacam_mining_indicators' GROUP BY source_key;`

- [ ] **112. Brazil ANM SIGMINE and Cadastro Mineiro** (`brazil_anm_sigmine_and_cadastro_mineiro`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=brazil_anm_sigmine_and_cadastro_mineiro/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 1 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'brazil_anm_sigmine_and_cadastro_mineiro' GROUP BY source_key;`

- [ ] **113. Peru INGEMMET GEOCATMIN** (`peru_ingemmet_geocatmin`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=peru_ingemmet_geocatmin/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'peru_ingemmet_geocatmin' GROUP BY source_key;`

- [ ] **114. ImportYeti shipment and supplier relationships** (`importyeti_shipment_and_supplier_relationships`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=importyeti_shipment_and_supplier_relationships/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'importyeti_shipment_and_supplier_relationships' GROUP BY source_key;`

- [ ] **115. ImportGenius international shipments** (`importgenius_international_shipments`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=importgenius_international_shipments/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'importgenius_international_shipments' GROUP BY source_key;`

- [ ] **116. MarineTraffic historical vessel tracks and port calls** (`marinetraffic_historical_vessel_tracks_and_port_calls`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=marinetraffic_historical_vessel_tracks_and_port_calls/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'marinetraffic_historical_vessel_tracks_and_port_calls' GROUP BY source_key;`

- [ ] **117. Kpler commodity cargo flows** (`kpler_commodity_cargo_flows`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=kpler_commodity_cargo_flows/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'kpler_commodity_cargo_flows' GROUP BY source_key;`

- [ ] **118. US Census International Trade API** (`us_census_international_trade_api`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=us_census_international_trade_api/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` (latest live failure only).  
  Current raw processing: Archives native observations with dimensions, units, flags, and timestamps; extracts normalized measurements for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'us_census_international_trade_api' GROUP BY source_key;`

- [ ] **119. Eurostat Comext goods trade** (`eurostat_comext_goods_trade`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=eurostat_comext_goods_trade/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 7 failed attempt(s).  
  Current raw processing: Archives native observations with dimensions, units, flags, and timestamps; extracts normalized measurements for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'eurostat_comext_goods_trade' GROUP BY source_key;`

- [ ] **120. Climate TRACE industrial assets and activity** (`climate_trace_industrial_assets_and_activity`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=climate_trace_industrial_assets_and_activity/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` (latest live failure only).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'climate_trace_industrial_assets_and_activity' GROUP BY source_key;`

### Day 9 — Thursday — 19 November 2026 (15 catalog entries)

- [ ] **121. Open Supply Hub production locations** (`open_supply_hub_production_locations`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=open_supply_hub_production_locations/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'open_supply_hub_production_locations' GROUP BY source_key;`

- [ ] **122. OpenStreetMap / Overpass industrial facilities** (`openstreetmap_overpass_industrial_facilities`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=openstreetmap_overpass_industrial_facilities/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'openstreetmap_overpass_industrial_facilities' GROUP BY source_key;`

- [ ] **123. Global Energy Monitor asset and ownership API** (`global_energy_monitor_asset_and_ownership_api`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=global_energy_monitor_asset_and_ownership_api/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 1 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'global_energy_monitor_asset_and_ownership_api' GROUP BY source_key;`

- [ ] **124. European Environment Agency industrial facilities** (`european_environment_agency_industrial_facilities`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=european_environment_agency_industrial_facilities/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'european_environment_agency_industrial_facilities' GROUP BY source_key;`

- [ ] **125. USDA FAS Production, Supply and Distribution** (`usda_fas_production_supply_and_distribution`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=usda_fas_production_supply_and_distribution/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` (latest live failure only).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'usda_fas_production_supply_and_distribution' GROUP BY source_key;`

- [ ] **126. Brazil ABVE electric vehicle registrations** (`brazil_abve_electric_vehicle_registrations`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=brazil_abve_electric_vehicle_registrations/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'brazil_abve_electric_vehicle_registrations' GROUP BY source_key;`

- [ ] **127. Brazil SENATRAN vehicle fleet** (`brazil_senatran_vehicle_fleet`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=brazil_senatran_vehicle_fleet/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 2 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'brazil_senatran_vehicle_fleet' GROUP BY source_key;`

- [ ] **128. IEA Global EV Data Explorer and Outlook** (`iea_global_ev_data_explorer_and_outlook`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=iea_global_ev_data_explorer_and_outlook/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'iea_global_ev_data_explorer_and_outlook' GROUP BY source_key;`

- [ ] **129. FAOSTAT food balances** (`faostat_food_balances`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=faostat_food_balances/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'faostat_food_balances' GROUP BY source_key;`

- [ ] **130. Euromonitor Passport Statistics API (paid candidate)** (`euromonitor_passport_statistics_api_paid_candidate`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=euromonitor_passport_statistics_api_paid_candidate/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'euromonitor_passport_statistics_api_paid_candidate' GROUP BY source_key;`

- [ ] **131. Meta Ad Library API** (`meta_ad_library_api`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=meta_ad_library_api/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'meta_ad_library_api' GROUP BY source_key;`

- [ ] **132. TikTok Commercial Content API** (`tiktok_commercial_content_api`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=tiktok_commercial_content_api/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'tiktok_commercial_content_api' GROUP BY source_key;`

- [ ] **133. LinkedIn Ad Library / external API** (`linkedin_ad_library_external_api`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=linkedin_ad_library_external_api/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'linkedin_ad_library_external_api' GROUP BY source_key;`

- [ ] **134. X Ads Repository DSA API** (`x_ads_repository_dsa_api`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=x_ads_repository_dsa_api/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'x_ads_repository_dsa_api' GROUP BY source_key;`

- [ ] **135. Sensor Tower / Pathmatics advertising intelligence (paid candidate)** (`sensor_tower_pathmatics_advertising_intelligence_paid_candidate`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=sensor_tower_pathmatics_advertising_intelligence_paid_candidate/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'sensor_tower_pathmatics_advertising_intelligence_paid_candidate' GROUP BY source_key;`

### Day 10 — Friday — 20 November 2026 (15 catalog entries)

- [ ] **136. Y Combinator company directory and cohorts** (`y_combinator_company_directory_and_cohorts`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=y_combinator_company_directory_and_cohorts/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'y_combinator_company_directory_and_cohorts' GROUP BY source_key;`

- [ ] **137. Techstars portfolio and cohorts** (`techstars_portfolio_and_cohorts`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=techstars_portfolio_and_cohorts/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'techstars_portfolio_and_cohorts' GROUP BY source_key;`

- [ ] **138. 500 Global portfolio and cohorts** (`500_global_portfolio_and_cohorts`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=500_global_portfolio_and_cohorts/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = '500_global_portfolio_and_cohorts' GROUP BY source_key;`

- [ ] **139. Antler early-stage portfolio** (`antler_early_stage_portfolio`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=antler_early_stage_portfolio/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'antler_early_stage_portfolio' GROUP BY source_key;`

- [ ] **140. Dealroom startup and funding API (commercial)** (`dealroom_startup_and_funding_api_commercial`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=dealroom_startup_and_funding_api_commercial/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'dealroom_startup_and_funding_api_commercial' GROUP BY source_key;`

- [ ] **141. Wefunder and Republic crowdfunding campaigns** (`wefunder_and_republic_crowdfunding_campaigns`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=wefunder_and_republic_crowdfunding_campaigns/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 3 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'wefunder_and_republic_crowdfunding_campaigns' GROUP BY source_key;`

- [ ] **142. OpenAlex scholarly graph** (`openalex_scholarly_graph`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=openalex_scholarly_graph/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives provider metadata and versioned full text; extracts source identity, provenance, and publication metadata for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'openalex_scholarly_graph' GROUP BY source_key;`

- [ ] **143. DataCite dissertations, datasets, software and usage** (`datacite_dissertations_datasets_software_and_usage`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=datacite_dissertations_datasets_software_and_usage/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:full_text`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:full_text` across 4 failed attempt(s).  
  Current raw processing: Archives provider metadata and versioned full text; extracts source identity, provenance, and publication metadata for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'datacite_dissertations_datasets_software_and_usage' GROUP BY source_key;`

- [ ] **144. OpenAIRE Graph projects and research products** (`openaire_graph_projects_and_research_products`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=openaire_graph_projects_and_research_products/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives provider metadata and versioned full text; extracts source identity, provenance, and publication metadata for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'openaire_graph_projects_and_research_products' GROUP BY source_key;`

- [ ] **145. bioRxiv / medRxiv preprints** (`biorxiv_medrxiv_preprints`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=biorxiv_medrxiv_preprints/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:full_text`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:full_text` across 4 failed attempt(s).  
  Current raw processing: Archives provider metadata and versioned full text; extracts source identity, provenance, and publication metadata for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'biorxiv_medrxiv_preprints' GROUP BY source_key;`

- [ ] **146. Open Science Framework projects and preregistrations** (`open_science_framework_projects_and_preregistrations`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=open_science_framework_projects_and_preregistrations/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'open_science_framework_projects_and_preregistrations' GROUP BY source_key;`

- [ ] **147. Zenodo research artifacts and usage** (`zenodo_research_artifacts_and_usage`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=zenodo_research_artifacts_and_usage/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` across 7 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'zenodo_research_artifacts_and_usage' GROUP BY source_key;`

- [ ] **148. Semantic Scholar citation context** (`semantic_scholar_citation_context`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=semantic_scholar_citation_context/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives provider metadata and versioned full text; extracts source identity, provenance, and publication metadata for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'semantic_scholar_citation_context' GROUP BY source_key;`

- [ ] **149. France theses.fr doctoral theses** (`france_theses_fr_doctoral_theses`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=france_theses_fr_doctoral_theses/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 1 failed attempt(s).  
  Current raw processing: Archives provider metadata and versioned full text; extracts source identity, provenance, and publication metadata for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'france_theses_fr_doctoral_theses' GROUP BY source_key;`

- [ ] **150. Brazil CAPES theses and dissertations** (`brazil_capes_theses_and_dissertations`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=brazil_capes_theses_and_dissertations/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:full_text`; `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives provider metadata and versioned full text; extracts source identity, provenance, and publication metadata for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'brazil_capes_theses_and_dissertations' GROUP BY source_key;`

### Day 11 — Monday — 23 November 2026 (8 catalog entries)

- [ ] **151. NSF research awards API** (`nsf_awards`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=nsf_awards/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `provider_request_projects_subset_of_raw_fields`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record`; `provider_request_projects_subset_of_raw_fields` across 7 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'nsf_awards' GROUP BY source_key;`

- [ ] **152. European Commission CORDIS** (`european_commission_cordis`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=european_commission_cordis/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'european_commission_cordis' GROUP BY source_key;`

- [ ] **153. Japan KAKEN funded research** (`japan_kaken_funded_research`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=japan_kaken_funded_research/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'japan_kaken_funded_research' GROUP BY source_key;`

- [ ] **154. Brazil FAPESP PIPE and grants** (`brazil_fapesp_pipe_and_grants`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=brazil_fapesp_pipe_and_grants/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'brazil_fapesp_pipe_and_grants' GROUP BY source_key;`

- [ ] **155. UKRI Gateway to Research** (`ukri_gateway_to_research`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=ukri_gateway_to_research/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'ukri_gateway_to_research' GROUP BY source_key;`

- [ ] **156. Hugging Face Hub models and datasets** (`hugging_face_hub_models_and_datasets`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=hugging_face_hub_models_and_datasets/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'hugging_face_hub_models_and_datasets' GROUP BY source_key;`

- [ ] **157. Altmetric scholarly attention (commercial)** (`altmetric_scholarly_attention_commercial`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=altmetric_scholarly_attention_commercial/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'altmetric_scholarly_attention_commercial' GROUP BY source_key;`

- [ ] **158. University technology-transfer catalogs and reports** (`university_technology_transfer_catalogs_and_reports`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=university_technology_transfer_catalogs_and_reports/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 2 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'university_technology_transfer_catalogs_and_reports' GROUP BY source_key;`

## Scope note

“Recorded raw-data errors” combines every distinct reason in the 31 October 2026 raw-error inventory with the latest live reason where the source remains restricted. It is raw-validation history; it does not claim that a source without an error has been fully verified.

