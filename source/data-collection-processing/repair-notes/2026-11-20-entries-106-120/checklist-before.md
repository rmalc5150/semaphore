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

- [x] **46. MLPerf benchmark results** (`mlperf_results`) — reviewed 13 November 2026, scoped pipeline verification  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=mlperf_results/`; checksummed originals linked in each record.  
  Source enabled under contract 2.0.3. SQL verified **451 row occurrences / 5 linked raw batches**, all 451 raw-complete for the declared record kind. Counts are observations, not unique recalls/results or completed history.  
  Published summary results, original supporting files and Git-tree inventories have distinct record kinds. Two older batches remain uncommitted and excluded because commit evidence is missing; current processing continues. This does not certify all benchmark artifacts, comparisons or historical availability.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'mlperf_results' GROUP BY source_key;`  
  All 3,028 saved validation rows tested across both sources passed; 65 tests passed. Capture/metadata/publication and all 15 historical executors checked, with enabled timers active. [Review evidence](repair-notes/2026-11-13-mlperf-cpsc/review-complete.json) · [SQL examples](repair-notes/2026-11-13-mlperf-cpsc/review-queries.sql).

- [x] **47. CPSC recalls** (`cpsc_recalls`) — reviewed 13 November 2026, scoped pipeline verification  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=cpsc_recalls/`; checksummed originals linked in each record.  
  Source enabled under contract 2.0.3. SQL verified **262 row occurrences / 16 linked raw batches**, all 262 raw-complete for the declared record kind. Counts are observations, not unique recalls/results or completed history.  
  Entire official recall records, including nested products, hazards and remedies, match original API responses. The overnight network backoff was cleared after normal transport recovery; today’s capture completed with 7 records. Image URLs are retained; image downloads, all incidents and historical vintages are outside this review.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'cpsc_recalls' GROUP BY source_key;`  
  All 3,028 saved validation rows tested across both sources passed; 65 tests passed. Capture/metadata/publication and all 15 historical executors checked, with enabled timers active. [Review evidence](repair-notes/2026-11-13-mlperf-cpsc/review-complete.json) · [SQL examples](repair-notes/2026-11-13-mlperf-cpsc/review-queries.sql).

- [x] **48. Federal Register** (`federal_register`, companion `federal_register_documents`) — reviewed 13 November 2026, scoped pipeline verification  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=federal_register/` and `raw/source=federal_register_documents/`; original API, XML/HTML and PDF links retained.  
  Both streams enabled under contract 2.0.3. Verified SQL snapshot: **145 listing observations / 16 full-notice observations**, all raw-complete for their distinct record kinds. Counts are row occurrences, not unique notices or historical completion.  
  Checked 100 saved inputs: 99 inputs / 446 rows passed; the one incomplete 2026-22743 capture was superseded by a newly committed, metadata-verified replacement with its 120,719,355-byte official PDF and 4,375,819-character extraction. Old raw evidence is preserved. Missing PDFs now stay queued for retry.  
  Scope: configured semiconductor, battery, robotics and clinical-trial searches. Full notice validation checks exact API identities, reparsed XML/HTML content and streamed official-PDF checksums. Large extractions are linked in S3. Current-law status, product applicability, exhaustive coverage and historical availability are not certified.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations FROM optima_metadata_engine.source_observations WHERE source_key IN ('federal_register','federal_register_documents') GROUP BY source_key;`  
  **83 tests passed.** Capture/metadata/publication and all 15 historical executors checked; enabled timers active. No new IAM, key or manual restart action for you. [Review evidence](repair-notes/2026-11-13-federal-register/review-complete.json) · [SQL examples](repair-notes/2026-11-13-federal-register/review-queries.sql).

- [x] **49. Trade screening lists** (`trade_screening`) — reviewed 13 November 2026, scoped Athena/publication verification  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=trade_screening/`; original provider exports remain linked in metadata.  
  Source **enabled**, with zero consecutive raw failures. The old SQL preview used `LIMIT 1`; the schedule's aggregate correctly returns one summary row, whose `observations` field is the actual count. The working preview now shows 25 individual named screening records.  
  Repaired a separate publication backlog: **18 validated batches / 576 observations** published and read back through Athena. Fresh total: **897 observations / 29 linked raw batches**, all raw-complete for their declared kinds; **896 named screening observations plus one older archive receipt**. Counts are observation occurrences, not unique people/entities or completed history.  
  Added trade screening to the existing bounded reviewed-source publication pass on m7. The controller dispatch timer and isolated streaming timer are active; remaining raw processing continues separately. Ten old inputs lacking checkpoint evidence and one discovery-only receipt remain excluded. Retired tracking enrichment stays retired.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations FROM optima_metadata_engine.source_observations WHERE source_key = 'trade_screening' GROUP BY source_key;`  
  **3 publication tests passed**, with successful fresh summary, 25-record preview and exact repaired-partition readbacks. This review checks Athena visibility and publication, not exhaustive sanctions coverage or screening/legal conclusions. [Review evidence](repair-notes/2026-11-13-trade-screening/review-complete.json) · [Individual-record SQL](repair-notes/2026-11-13-trade-screening/review-queries.sql).

- [x] **50. USGS minerals** (`usgs_minerals`) — reviewed 14 November 2026, scoped raw-material/SQL verification  
  Fresh Athena check: **84 published observations**, all with complete raw status for their declared record kinds; counts are occurrences, not unique records or completed history. Both committed-data and metadata previews returned substantive rows.  
  Two 2026 lithium/cobalt PDFs matched their originals, reparsed text, statistics, footnotes and sections. The background metadata queue remains **raw_stopped** after four older validation failures, plus one missing-object retry; this finding is open. Published rows remain queryable. This checkbox covers existing raw material/SQL, not recovery of that queue or full history.  
  Two raw records checked per source with official-original checksums and collection manifest/checkpoint evidence. Processing for this verification ran on m7; production settings and deliberate pauses are unchanged.  
  [Review evidence and remaining findings](repair-notes/2026-11-14-six-source-review/review-complete.json) · [Verified SQL examples](repair-notes/2026-11-14-six-source-review/review-queries.sql).

- [x] **51. UN Comtrade** (`un_comtrade`) — reviewed 13 November 2026, scoped raw/metadata/Athena pipeline  
  Source enabled under contract 2.0.3. Replaced generic false raw failures with exact official response/row, identity, query-dimension, year and truncation checks. Provider quantities, units, nulls and estimation flags are retained.  
  Verified SQL snapshot: **14 observations / 14 linked raw batches**, all raw-complete; latest captured input **2026-11-13T11:00:27.328698Z**. Two older 2021 inputs also passed original-byte and collection-commit checks. Counts are occurrences, not unique trade flows.  
  Scope: configured five reporters, four battery/mineral HS6 commodities, annual imports/exports and world partner totals. Historical route has checkpointed successes and reports its configured target drained; exhaustive coverage and historical vintages are not certified. Daily capture and all enabled schedules checked. No new key/IAM action required.  
  [Working SQL](repair-notes/2026-11-13-comtrade-doe/review-queries.sql) · [Review evidence](repair-notes/2026-11-13-comtrade-doe/review-complete.json).

- [x] **52. Department of Energy storage program** (`doe_storage_program` and document/technical/funding companions) — reviewed 13 November 2026, scoped raw/metadata/Athena pipeline  
  All four streams enabled under contract 2.0.3. Verified SQL snapshot: **54 observations**: 14 program/original-document, 13 document-summary, 13 technical-evidence and 14 funding-evidence rows, all raw-complete for their declared kinds. These are occurrences, not unique documents or certified results.  
  Originals, deterministic reparsing, saved extraction/fact/table mapping and URL/semantic identities are checked. Two older PDFs also passed commit/original checks. The archived long-duration storage report is visible in Athena with its full original PDF and 117,216 extracted characters. Extraction limits remain explicit.  
  Public discovery now follows storage main content and linked official reports, with new retained daily/historical frontiers. Excluded 55 discovery receipts and 25 unrelated DOE history/administrative receipts; originals retained. One old input lacking committed-history evidence remains excluded. Tracking-based enrichment stays retired.  
  Current daily and historical capture, metadata lanes and all enabled schedules checked. The bounded recurring publisher uses an independent lock on m7 and completed successfully. Full archive coverage, normalized performance, recipient allocation and actual payments are not certified.  
  [Working SQL](repair-notes/2026-11-13-comtrade-doe/review-queries.sql) · [Review evidence](repair-notes/2026-11-13-comtrade-doe/review-complete.json).

- [x] **53. EIA battery generators** (`eia_battery_generators`) — reviewed 14 November 2026, scoped raw-material/SQL verification  
  Fresh Athena check: **13,085 published observations**, all with complete raw status for their declared record kinds; counts are occurrences, not unique records or completed history. Both committed-data and metadata previews returned substantive rows.  
  Two September 2026 Planned/Operating generator rows matched the official workbook, sheet, Plant ID, Generator ID and all retained columns. Inventory statuses/units remain explicit; dispatch, firm capacity and supplier/entity matching are outside scope. The source is enabled; two older inputs lacking checkpoint evidence remain excluded.  
  Two raw records checked per source with official-original checksums and collection manifest/checkpoint evidence. Processing for this verification ran on m7; production settings and deliberate pauses are unchanged.  
  [Review evidence and remaining findings](repair-notes/2026-11-14-six-source-review/review-complete.json) · [Verified SQL examples](repair-notes/2026-11-14-six-source-review/review-queries.sql).

- [ ] **54. EIA generator index** (`eia_generator_index`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=eia_generator_index/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record`; `public_capture_is_discovery_page_only` across 7 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for `specialist_inputs`.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'eia_generator_index' GROUP BY source_key;`

- [x] **55. EIA retail prices** (`eia_retail_prices`) — reviewed 14 November 2026, scoped raw-material/SQL verification  
  Fresh Athena check: **322 published observations**, all with complete raw status for their declared record kinds; counts are occurrences, not unique records or completed history. Both committed-data and metadata previews returned substantive rows.  
  Two saved US/all-sector monthly rows matched original API responses, identities and price/sales/revenue/customer units. These are average retail statistics, not wholesale prices or site tariffs. Source enabled; no failed/retry/uncommitted metadata jobs in the scoped control check.  
  Two raw records checked per source with official-original checksums and collection manifest/checkpoint evidence. Processing for this verification ran on m7; production settings and deliberate pauses are unchanged.  
  [Review evidence and remaining findings](repair-notes/2026-11-14-six-source-review/review-complete.json) · [Verified SQL examples](repair-notes/2026-11-14-six-source-review/review-queries.sql).

- [x] **56. California ISO prices** (`caiso_prices`) — reviewed 14 November 2026, scoped raw-material/SQL verification  
  Fresh Athena check: **16,256 published observations**, all with complete raw status for their declared record kinds; counts are occurrences, not unique records or completed history. Both committed-data and metadata previews returned substantive rows.  
  Two DAM price components matched official ZIP/member provenance, exact native rows, prices and interval timing. Negative values are retained. This covers caiso_prices only, not all nodes, ancillary datasets, storage indicators or profitability. Source enabled; one older input lacking checkpoint evidence remains excluded.  
  Two raw records checked per source with official-original checksums and collection manifest/checkpoint evidence. Processing for this verification ran on m7; production settings and deliberate pauses are unchanged.  
  [Review evidence and remaining findings](repair-notes/2026-11-14-six-source-review/review-complete.json) · [Verified SQL examples](repair-notes/2026-11-14-six-source-review/review-queries.sql).

- [x] **57. BLS wages** (`bls_wages`) — reviewed 14 November 2026, scoped raw-material/SQL verification  
  Fresh Athena check: **802 published observations**, all with complete raw status for their declared record kinds; counts are occurrences, not unique records or completed history. Both committed-data and metadata previews returned substantive rows.  
  Two CES3000000003 observations matched original BLS series rows, periods, values and footnotes. Units are seasonally adjusted manufacturing average hourly earnings in USD/hour, not fully loaded customer labor costs. Source enabled; two older inputs lacking checkpoint evidence remain excluded.  
  Two raw records checked per source with official-original checksums and collection manifest/checkpoint evidence. Processing for this verification ran on m7; production settings and deliberate pauses are unchanged.  
  [Review evidence and remaining findings](repair-notes/2026-11-14-six-source-review/review-complete.json) · [Verified SQL examples](repair-notes/2026-11-14-six-source-review/review-queries.sql).

- [x] **58. Research Organization Registry institutions** (`ror_institutions`) — reviewed 14 November 2026, scoped raw-material/SQL verification  
  Fresh Athena check: **141 published observations**, all with complete raw status for their declared record kinds; counts are occurrences, not unique records or completed history. Both committed-data and metadata previews returned substantive rows.  
  Two entire institution records matched original ROR v2 responses, IDs, names, relationships and status. These are current identity candidates, not verified grant affiliations or historical vintages. Source enabled; one older public-receipt validation failure and two uncommitted inputs remain recorded.  
  Two raw records checked per source with official-original checksums and collection manifest/checkpoint evidence. Processing for this verification ran on m7; production settings and deliberate pauses are unchanged.  
  [Review evidence and remaining findings](repair-notes/2026-11-14-six-source-review/review-complete.json) · [Verified SQL examples](repair-notes/2026-11-14-six-source-review/review-queries.sql).

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

- [x] **62. SAM.gov opportunities** (`sam_gov_opportunities`)  
  Raw S3 (original provider bytes): `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/sam_gov_opportunities/`  
  Normalized input / file receipts: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=sam_gov_opportunities/dataset=specialist_inputs/`  
  Current collection state: **metadata enabled** — checked 14 November 2026; capture exceptions below.  
  Recorded raw-data errors: Original inventory retained in repair evidence; current validation and capture findings below.  
  Current raw processing: Native SAM notice records matched their complete saved search pages. Three older failures (2,009 notices) were generic-validator false negatives; repaired under a notice-metadata contract. Descriptions/attachments are separate linked resources. Daily timer succeeded. The legacy authenticated historical timer remains disabled with migration requirements; no separate SAM historical route was established by this audit. This is an open capture finding, not proof of full history.  
  Athena SQL: `SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'sam_gov_opportunities' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;`

  RM: yes
  SQL: yes

  **Reviewed 14 November 2026 — raw/SQL verified; daily, historical and metadata lanes inspected.** Fresh readback: **21,790 observations**, all raw-complete within the declared record/file scope. Published occurrences do not mean the backfill is finished.  
  [Review evidence and open findings](repair-notes/2026-11-14-entries-62-75/review-complete.json) · [Actual S3 locators](repair-notes/2026-11-14-entries-62-75/raw-s3-locators.json) · [Verified SQL](repair-notes/2026-11-14-entries-62-75/review-queries.sql).

- [x] **63. USPTO Office Actions** (`uspto_odp`)  
  Raw S3 (original provider bytes): `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/uspto_odp/`  
  Normalized input / file receipts: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=uspto_odp/dataset=patent_office_actions/`  
  Current collection state: **metadata enabled** — checked 14 November 2026; capture exceptions below.  
  Recorded raw-data errors: Original inventory retained in repair evidence; current validation and capture findings below.  
  Current raw processing: Office-action API record and actual USPTO PDF checksum, document/application identity and PDF parse verified. The pasted raw stop was stale: uspto_odp is enabled under contract 2.0.3. Daily and historical prosecution streams share the successful m7 tick. Query now filters patent_office_actions; general patent bibliography cannot satisfy this entry. Ten source-wide inputs remain uncommitted and are withheld until their collection manifests exist.  
  Athena SQL: `SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'uspto_odp' AND dataset = 'patent_office_actions' GROUP BY source_key, dataset;`

  RM: yes
  SQL: yes

  **Reviewed 14 November 2026 — raw/SQL verified; daily, historical and metadata lanes inspected.** Fresh readback: **95 observations**, all raw-complete within the declared record/file scope. Published occurrences do not mean the backfill is finished.  
  [Review evidence and open findings](repair-notes/2026-11-14-entries-62-75/review-complete.json) · [Actual S3 locators](repair-notes/2026-11-14-entries-62-75/raw-s3-locators.json) · [Verified SQL](repair-notes/2026-11-14-entries-62-75/review-queries.sql).

- [x] **64. USPTO final Petition Decisions** (`uspto_odp`)  
  Raw S3 (original provider bytes): `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/uspto_odp/`  
  Normalized input / file receipts: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=uspto_odp/dataset=patent_petition_decisions/`  
  Current collection state: **metadata enabled** — checked 14 November 2026; capture exceptions below.  
  Recorded raw-data errors: Original inventory retained in repair evidence; current validation and capture findings below.  
  Current raw processing: Petition-decision API record and actual USPTO PDF checksum, application identity and PDF parse verified. Daily and historical prosecution streams share the successful m7 tick. Query now filters patent_petition_decisions. Ten source-wide uncommitted inputs remain withheld; no claim of exhaustive prosecution history.  
  Athena SQL: `SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'uspto_odp' AND dataset = 'patent_petition_decisions' GROUP BY source_key, dataset;`

  RM: yes
  SQL: yes

  **Reviewed 14 November 2026 — raw/SQL verified; daily, historical and metadata lanes inspected.** Fresh readback: **95 observations**, all raw-complete within the declared record/file scope. Published occurrences do not mean the backfill is finished.  
  [Review evidence and open findings](repair-notes/2026-11-14-entries-62-75/review-complete.json) · [Actual S3 locators](repair-notes/2026-11-14-entries-62-75/raw-s3-locators.json) · [Verified SQL](repair-notes/2026-11-14-entries-62-75/review-queries.sql).

- [x] **65. BIS SDMX API** (`bis_sdmx_api`)  
  Raw S3 (original provider bytes): `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/bis_sdmx_api/`  
  Normalized input / file receipts: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/athena/`  
  Current collection state: **metadata enabled** — checked 14 November 2026; capture exceptions below.  
  Recorded raw-data errors: Original inventory retained in repair evidence; current validation and capture findings below.  
  Current raw processing: The missing folder was an incorrect locator. Native policy-rate CSVs are under constellation-backfill/public-capture/objects/bis_sdmx_api/. Two complete files (about 59 MB each) passed SHA-256/size and CSV-header checks on m7. Daily frontier succeeded today, historical file route is drained. SQL counts archived-file metadata, not individual policy-rate measurements; selected BIS dataflow only.  
  Athena SQL: `SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'bis_sdmx_api' AND dataset = 'public_documents' GROUP BY source_key, dataset;`

  Can't find S3 folder. 
  SQL: yes

  **Reviewed 14 November 2026 — raw/SQL verified; daily, historical and metadata lanes inspected.** Fresh readback: **8 observations**, all raw-complete within the declared record/file scope. Published occurrences do not mean the backfill is finished.  
  [Review evidence and open findings](repair-notes/2026-11-14-entries-62-75/review-complete.json) · [Actual S3 locators](repair-notes/2026-11-14-entries-62-75/raw-s3-locators.json) · [Verified SQL](repair-notes/2026-11-14-entries-62-75/review-queries.sql).

- [x] **66. FRED / ALFRED series and vintages** (`fred_alfred_series_and_vintages`)  
  Raw S3 (original provider bytes): `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/fred_alfred_series_and_vintages/`  
  Normalized input / file receipts: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=fred_alfred_series_and_vintages/dataset=specialist_inputs/`  
  Current collection state: **metadata enabled** — checked 14 November 2026; capture exceptions below.  
  Recorded raw-data errors: Original inventory retained in repair evidence; current validation and capture findings below.  
  Current raw processing: Two saved FRED observations matched exact original date/value/realtime intervals. Daily and historical routes are enabled and have successful captures. Open scheduler exceptions include ALFRED vintages the provider says are unavailable, older HTTP 400s and date-scope failures. These remain visible; missing vintages are not synthesized or treated as zeros. Configured series only, not all FRED.  
  Athena SQL: `SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'fred_alfred_series_and_vintages' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;`

  RM: yes
  SQL: yes

  **Reviewed 14 November 2026 — raw/SQL verified; daily, historical and metadata lanes inspected.** Fresh readback: **17,183 observations**, all raw-complete within the declared record/file scope. Published occurrences do not mean the backfill is finished.  
  [Review evidence and open findings](repair-notes/2026-11-14-entries-62-75/review-complete.json) · [Actual S3 locators](repair-notes/2026-11-14-entries-62-75/raw-s3-locators.json) · [Verified SQL](repair-notes/2026-11-14-entries-62-75/review-queries.sql).

- [x] **67. UNIDO IIP and INDSTAT** (`unido_iip_and_indstat`)  
  Raw S3 (original provider bytes): `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/unido_iip_and_indstat/`  
  Normalized input / file receipts: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=unido_iip_and_indstat/dataset=specialist_inputs/`  
  Current collection state: **metadata enabled** — checked 14 November 2026; capture exceptions below.  
  Recorded raw-data errors: Original inventory retained in repair evidence; current validation and capture findings below.  
  Current raw processing: Old SQL rows described catalogues, not industrial measurements. Added native UNIDO getData capture with dynamic dataset IDs and country/variable/activity/period provenance, plus m7 historical dispatch and daily rotation. Historical and daily proof captures passed for both IIP and INDSTAT/4. Suppressed/aggregation footnote cells are retained without inventing zeros. SQL below excludes legacy public_documents catalogues. Backfill remains in progress.  
  Athena SQL: `SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'unido_iip_and_indstat' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;`

  No S3 bucket
  SQL: yes

  **Reviewed 14 November 2026 — raw/SQL verified; daily, historical and metadata lanes inspected.** Fresh readback: **1,056 observations**, all raw-complete within the declared record/file scope. Published occurrences do not mean the backfill is finished.  
  [Review evidence and open findings](repair-notes/2026-11-14-entries-62-75/review-complete.json) · [Actual S3 locators](repair-notes/2026-11-14-entries-62-75/raw-s3-locators.json) · [Verified SQL](repair-notes/2026-11-14-entries-62-75/review-queries.sql).

- [x] **68. ILOSTAT labor statistics** (`ilostat_labor_statistics`)  
  Raw S3 (original provider bytes): `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/ilostat_labor_statistics/`  
  Normalized input / file receipts: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/athena/`  
  Current collection state: **metadata enabled** — checked 14 November 2026; capture exceptions below.  
  Recorded raw-data errors: Original inventory retained in repair evidence; current validation and capture findings below.  
  Current raw processing: The missing folder was an incorrect locator. Original gzip-compressed RDS files are under constellation-backfill/public-capture/objects/ilostat_labor_statistics/. Two files passed SHA-256/size, full gzip integrity and R serialization framing checks. Daily frontier succeeded today; historical snapshot route is drained. SQL rows describe archived files, not extracted labor observations. Forecast/observation and vintage extraction remain unimplemented.  
  Athena SQL: `SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'ilostat_labor_statistics' AND dataset = 'public_documents' GROUP BY source_key, dataset;`

  No S3 bucket
  SQL: yes

  **Reviewed 14 November 2026 — raw/SQL verified; daily, historical and metadata lanes inspected.** Fresh readback: **8 observations**, all raw-complete within the declared record/file scope. Published occurrences do not mean the backfill is finished.  
  [Review evidence and open findings](repair-notes/2026-11-14-entries-62-75/review-complete.json) · [Actual S3 locators](repair-notes/2026-11-14-entries-62-75/raw-s3-locators.json) · [Verified SQL](repair-notes/2026-11-14-entries-62-75/review-queries.sql).

- [x] **69. IMF PortWatch shipping activity** (`imf_portwatch_shipping_activity`)  
  Raw S3 (original provider bytes): `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/imf_portwatch_shipping_activity/`  
  Normalized input / file receipts: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=imf_portwatch_shipping_activity/dataset=specialist_inputs/`  
  Current collection state: **metadata enabled** — checked 14 November 2026; capture exceptions below.  
  Recorded raw-data errors: Original inventory retained in repair evidence; current validation and capture findings below.  
  Current raw processing: Replaced website-discovery-only input with the IMF native ArcGIS port/day table. m7 captured and validated all 2,065 port rows for 2019-01-01 and for 2026-11-06, then published metadata. Recurring historical dispatcher and m7 daily rotation are active; obsolete discovery inputs were superseded with evidence retained. Provider availability starts 2019-01-01, not 2016; daily uses a seven-day lag. Estimates are not customs shipments; backfill is ongoing.  
  Athena SQL: `SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'imf_portwatch_shipping_activity' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;`

  No S3 bucket
  SQL: no

  **Reviewed 14 November 2026 — raw/SQL verified; daily, historical and metadata lanes inspected.** Fresh readback: **993 observations**, all raw-complete within the declared record/file scope. Published occurrences do not mean the backfill is finished.  
  [Review evidence and open findings](repair-notes/2026-11-14-entries-62-75/review-complete.json) · [Actual S3 locators](repair-notes/2026-11-14-entries-62-75/raw-s3-locators.json) · [Verified SQL](repair-notes/2026-11-14-entries-62-75/review-queries.sql).

- [x] **70. Ember electricity demand and generation** (`ember_electricity_demand_and_generation`)  
  Raw S3 (original provider bytes): `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/ember_electricity_demand_and_generation/`  
  Normalized input / file receipts: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=ember_electricity_demand_and_generation/dataset=specialist_inputs/`  
  Current collection state: **metadata enabled** — checked 14 November 2026; capture exceptions below.  
  Recorded raw-data errors: Original inventory retained in repair evidence; current validation and capture findings below.  
  Current raw processing: Corrected validation against the exact archived monthly Ember response, including count, units/aggregation flags and attribution. All 20 formerly failed batches passed original checks, source re-enabled, pending jobs migrated and publication verified. Daily capture is current; historical configured scopes were completed. Missing releases remain missing, not zero.  
  Athena SQL: `SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'ember_electricity_demand_and_generation' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;`

  RM: yes
  SQl: yes

  **Reviewed 14 November 2026 — raw/SQL verified; daily, historical and metadata lanes inspected.** Fresh readback: **2,560 observations**, all raw-complete within the declared record/file scope. Published occurrences do not mean the backfill is finished.  
  [Review evidence and open findings](repair-notes/2026-11-14-entries-62-75/review-complete.json) · [Actual S3 locators](repair-notes/2026-11-14-entries-62-75/raw-s3-locators.json) · [Verified SQL](repair-notes/2026-11-14-entries-62-75/review-queries.sql).

- [x] **71. WTO Timeseries API** (`wto_timeseries_api`)  
  Raw S3 (original provider bytes): `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/wto_timeseries_api/`  
  Normalized input / file receipts: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=wto_timeseries_api/dataset=specialist_inputs/`  
  Current collection state: **metadata enabled** — checked 14 November 2026; capture exceptions below.  
  Recorded raw-data errors: Original inventory retained in repair evidence; current validation and capture findings below.  
  Current raw processing: Two entire WTO observation rows matched original Dataset responses, including indicator, reporting economy, period, unit and value. Daily/historical routes and metadata are enabled. Saved HTTP/network failures and source-change refreshes remain retryable capture findings; no blanket historical completion claim or all bilateral/product combinations claim.  
  Athena SQL: `SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'wto_timeseries_api' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;`

  RM: yes
  SQL: yes

  **Reviewed 14 November 2026 — raw/SQL verified; daily, historical and metadata lanes inspected.** Fresh readback: **22,529 observations**, all raw-complete within the declared record/file scope. Published occurrences do not mean the backfill is finished.  
  [Review evidence and open findings](repair-notes/2026-11-14-entries-62-75/review-complete.json) · [Actual S3 locators](repair-notes/2026-11-14-entries-62-75/raw-s3-locators.json) · [Verified SQL](repair-notes/2026-11-14-entries-62-75/review-queries.sql).

- [x] **72. WTO Quantitative Restrictions API** (`wto_quantitative_restrictions_api`)  
  Raw S3 (original provider bytes): `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/wto_quantitative_restrictions_api/`  
  Normalized input / file receipts: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=wto_quantitative_restrictions_api/dataset=specialist_inputs/`  
  Current collection state: **metadata enabled** — checked 14 November 2026; capture exceptions below.  
  Recorded raw-data errors: Original inventory retained in repair evidence; current validation and capture findings below.  
  Current raw processing: Full native restriction/notification JSON is saved under source_documents/wto_quantitative_restrictions_api/, beyond the URL fields visible in normalized rows. Corrected endpoint/identity/date/pagination validation, replayed formerly failed inputs and verified nonempty Athena publication. Daily and configured historical scopes succeeded. Linked documents and current legal effect remain separate.  
  Athena SQL: `SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'wto_quantitative_restrictions_api' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;`

  RM: just point to orginal URLs, no raw material
  SQL: no

  **Reviewed 14 November 2026 — raw/SQL verified; daily, historical and metadata lanes inspected.** Fresh readback: **1,212 observations**, all raw-complete within the declared record/file scope. Published occurrences do not mean the backfill is finished.  
  [Review evidence and open findings](repair-notes/2026-11-14-entries-62-75/review-complete.json) · [Actual S3 locators](repair-notes/2026-11-14-entries-62-75/raw-s3-locators.json) · [Verified SQL](repair-notes/2026-11-14-entries-62-75/review-queries.sql).

- [x] **73. WTO ePing SPS/TBT notifications** (`wto_eping_sps_tbt_notifications`)  
  Raw S3 (original provider bytes): `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/wto_eping_sps_tbt_notifications/`  
  Normalized input / file receipts: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=wto_eping_sps_tbt_notifications/dataset=specialist_inputs/`  
  Current collection state: **metadata enabled** — checked 14 November 2026; capture exceptions below.  
  Recorded raw-data errors: Original inventory retained in repair evidence; current validation and capture findings below.  
  Current raw processing: Corrected metadata validation against the exact original ePing notification page and distribution-date query window, including older saved scopes. Replayed and published verified rows. Daily and configured historical captures succeeded. Entire returned English notification metadata is retained; document links are not a claim that attachments were downloaded.  
  Athena SQL: `SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'wto_eping_sps_tbt_notifications' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;`

  RM: yes
  SQL no

  **Reviewed 14 November 2026 — raw/SQL verified; daily, historical and metadata lanes inspected.** Fresh readback: **1,215 observations**, all raw-complete within the declared record/file scope. Published occurrences do not mean the backfill is finished.  
  [Review evidence and open findings](repair-notes/2026-11-14-entries-62-75/review-complete.json) · [Actual S3 locators](repair-notes/2026-11-14-entries-62-75/raw-s3-locators.json) · [Verified SQL](repair-notes/2026-11-14-entries-62-75/review-queries.sql).

- [x] **74. EPO OPS patent legal events** (`epo_ops_patent_legal_events`)  
  Raw S3 (original provider bytes): `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/epo_ops_patent_legal_events/`  
  Normalized input / file receipts: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=epo_ops_patent_legal_events/dataset=specialist_inputs/`  
  Current collection state: **metadata enabled** — checked 14 November 2026; capture exceptions below.  
  Recorded raw-data errors: Original inventory retained in repair evidence; current validation and capture findings below.  
  Current raw processing: Corrected validation of original EPO legal-event XML, event/family identity and distinct gazette/effective/created/exchanged dates; replayed and published verified rows. Daily/historical capture remains enabled, with older provider HTTP 500s and quota deferrals recorded. Candidate applicant matches and current legal title are unverified.  
  Athena SQL: `SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'epo_ops_patent_legal_events' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;`

  RM: yes
  SQL: no

  **Reviewed 14 November 2026 — raw/SQL verified; daily, historical and metadata lanes inspected.** Fresh readback: **227 observations**, all raw-complete within the declared record/file scope. Published occurrences do not mean the backfill is finished.  
  [Review evidence and open findings](repair-notes/2026-11-14-entries-62-75/review-complete.json) · [Actual S3 locators](repair-notes/2026-11-14-entries-62-75/raw-s3-locators.json) · [Verified SQL](repair-notes/2026-11-14-entries-62-75/review-queries.sql).

- [x] **75. Copernicus ERA5 / ERA5-Land** (`copernicus_era5_era5_land`)  
  Raw S3 (original provider bytes): `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/copernicus_era5_era5_land/`  
  Normalized input / file receipts: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=copernicus_era5_era5_land/dataset=specialist_inputs/`  
  Current collection state: **metadata enabled** — checked 14 November 2026; capture exceptions below.  
  Recorded raw-data errors: Original inventory retained in repair evidence; current validation and capture findings below.  
  Current raw processing: Two complete saved NetCDF artifacts passed checksum/signature checks, including a ZIP with verified NetCDF members; SQL remains nonempty. Found current successful CDS jobs whose download assets had expired. Installed conditional expiry recovery that retains old job receipts and resubmits under the existing two-job limit. A previously failing scope now has a fresh verified NetCDF download and an accepted, published metadata release; exact-job recovery proof is saved separately. Historical and daily lanes remain active. Eight configured reference cells only; structured weather extraction remains pending.  
  Athena SQL: `SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'copernicus_era5_era5_land' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;`
RM: yes
SQL: yes

  **Reviewed 14 November 2026 — raw/SQL verified; daily, historical and metadata lanes inspected.** Fresh readback: **172 observations**, all raw-complete within the declared record/file scope. Published occurrences do not mean the backfill is finished.  
  [Review evidence and open findings](repair-notes/2026-11-14-entries-62-75/review-complete.json) · [Actual S3 locators](repair-notes/2026-11-14-entries-62-75/raw-s3-locators.json) · [Verified SQL](repair-notes/2026-11-14-entries-62-75/review-queries.sql).

### Day 6 — Monday — 16 November 2026 (15 catalog entries)

- [x] **76. NASA POWER weather and solar resource** (`nasa_power_weather_and_solar_resource`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/nasa_power_weather_and_solar_resource/` (provider originals); `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=nasa_power_weather_and_solar_resource/` (committed row batches).
  Current collection state: **enabled** — daily/historical capture and metadata queues checked on 16 November 2026  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Native NASA measurements were checked against the saved complete provider response, including parameter values and units. Daily capture and the configured historical scopes are healthy; the eight reference locations are a bounded geographic scope.  
  Athena SQL (bounded published sample, not a source total): `SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'nasa_power_weather_and_solar_resource' AND contract_version = '2.0.2' AND job_id IN ('002565768e416cb6727c726186823352ea2537160b7ed5d090120cd8cbd2a4e6', '00eed946e9b41bf6153e1442692e8d2e79a9a540e68b377d83175bf468fc4f4c', '01507966c490f7590ae0a7954df1e143d6d7693f21b5634673052fbe8612b0f3', '017eec1ee3c217e279a30eddcbfd6ac89d98cfa9e899b80430221a8bd8e43205', '018a01f18a5ce8a19e1c7e684b2938330adb8f2ace1193ddcbde1cf01008e00c') GROUP BY source_key, dataset;`

  RM: yes
  SQL: yes

  Review (16 November 2026): **reviewed** — 135 complete published sample rows. Native NASA measurements were checked against the saved complete provider response, including parameter values and units. Daily capture and the configured historical scopes are healthy; the eight reference locations are a bounded geographic scope. Evidence: [review report](repair-notes/2026-11-16-entries-76-90/review-report.md). Original owner RM/SQL notes above are retained as the pre-repair observations.

- [x] **77. USGS Earthquake Catalog API** (`usgs_earthquakes`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/usgs_earthquakes/` (daily); historical example: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/jobs/ef98722cff7dd7c3f6c6ee16bf46f9a02d58aa1d57dbd013cf0f650c916aa349/attempts/a3eaf20b54894529bbe8ebfc90da8911/raw/a2d4ff767f558e2e2bf53cdd37ccf35bf57541bb786c61b05ad76d1afc3997ca`.
  Current collection state: **enabled** — daily/historical capture and metadata queues checked on 16 November 2026  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: The missing folder was a locator error. Daily GeoJSON originals live under public-capture/objects/usgs_earthquakes; historical originals are linked from native job manifests. All 3,951 registered historical query partitions succeeded and the seven current daily windows completed; this does not certify every possible earthquake query or original vintage.  
  Athena SQL (bounded published sample, not a source total): `SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'usgs_earthquakes' AND contract_version = '2.0.2' AND job_id IN ('00ba868baf2b73d76073980ee5514974f97bd2d76f9237d78ed9c5f3f73c9b31', '012e78fe7260b3629dcd9f24a566b98aafecf60c212202eb1daf40ceffe1a94a', '01b84b0dfab55ed568e76267b227fab2961a9a3ed8bb27d44a700ff40181a681', '01bbde93ee3a577de5f94fe26998d796167aae269cb8a457c3eac004939ffee9') GROUP BY source_key, dataset;`

  RM: no S3 folder
  SQL: yes

  Review (16 November 2026): **reviewed** — 128 complete published sample rows. The missing folder was a locator error. Daily GeoJSON originals live under public-capture/objects/usgs_earthquakes; historical originals are linked from native job manifests. All 3,951 registered historical query partitions succeeded and the seven current daily windows completed; this does not certify every possible earthquake query or original vintage. Evidence: [review report](repair-notes/2026-11-16-entries-76-90/review-report.md). Original owner RM/SQL notes above are retained as the pre-repair observations.

- [x] **78. UCDP organized violence** (`ucdp_organized_violence`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/ucdp_organized_violence/`
  Current collection state: **enabled** — daily/historical capture and metadata queues checked on 16 November 2026  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Added official UCDP GED ZIP and candidate CSV acquisition, checksums, whole-archive CRC/structure checks, metadata validation and publication. Daily and historical public-file routes completed their present frontiers. Public downloads work without the separately authenticated UCDP API.  
  Athena SQL (bounded published sample, not a source total): `SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'ucdp_organized_violence' AND contract_version = '2.0.3' AND job_id IN ('43ebe1db1e0a565738657a3e79166136fc272276db63809ce8ae0938495805d0', '9abe4a47193d54e81ee70157858b0cad93c6aa22a94b7cadf74561415e371878') GROUP BY source_key, dataset;`

  RM: no S3 folder
  SQL: no

  Review (16 November 2026): **reviewed** — 2 complete published sample rows. Added official UCDP GED ZIP and candidate CSV acquisition, checksums, whole-archive CRC/structure checks, metadata validation and publication. Daily and historical public-file routes completed their present frontiers. Public downloads work without the separately authenticated UCDP API. Evidence: [review report](repair-notes/2026-11-16-entries-76-90/review-report.md). Original owner RM/SQL notes above are retained as the pre-repair observations.

- [ ] **79. arXiv early technical disclosures** (`arxiv`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/arxiv/` (daily); historical example: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/jobs/027db69986966e1bde98f5618ccf3575cfbc4a1dff4d95d60f119244d09a3f7e/attempts/9297cac901e04d619727d77d61aa7978/raw/053b4ebebf76cf634c5438c79e759cc4e7695dac9cf2f06e02fc0fed1133dffa`.
  Current collection state: **enabled** — daily/historical capture and metadata queues checked on 16 November 2026  
  Recorded raw-data errors: `missing_verified_raw_artifacts:full_text` across 4 failed attempt(s).  
  Current raw processing: Citation and abstract processing is repaired and published under contract 2.0.3; all 400 records from the four former failed batches matched saved Atom originals. These are metadata/abstracts, not full papers. Full-text acquisition remains outstanding, so this entry is not fully reviewed. An older daily snapshot stopped on duplicate provider IDs; its replacement query completed with 1,647 records, all were validated against native Atom originals, and only the exact incomplete metadata input was superseded. Original bytes remain retained; replacement metadata processing is queued.  
  Athena SQL (bounded published sample, not a source total): `SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'arxiv' AND contract_version = '2.0.3' AND job_id IN ('0eda391b934be0f3bd7b88a36ee572a652f3309fd46e1d031d32188773ddcc1b', '1d22ad5a415479481a7fff7d3faf0a1d63f2ef479bf387cccdaca8206aa546e9', '30587ca1f2be9650772f684032adf2a9aa96ee1341378e151930a092868d86b6', '36b2d8c47ae1f352f9cacda68af1f99ed32e269f08cdfb176e63859cd04697d1', '370d35cf12eceee55049b7e0ed8f26853e0a55ce7c125247c4dcb6ece3bbdae7') GROUP BY source_key, dataset;`

  RM: no S3 folder
  SQL: no

  Review (16 November 2026): **partial — not fully reviewed** — 104 complete published sample rows. Citation and abstract processing is repaired and published under contract 2.0.3; all 400 records from the four former failed batches matched saved Atom originals. These are metadata/abstracts, not full papers. Full-text acquisition remains outstanding, so this entry is not fully reviewed. An older daily snapshot stopped on duplicate provider IDs; its replacement query completed with 1,647 records, all were validated against native Atom originals, and only the exact incomplete metadata input was superseded. Original bytes remain retained; replacement metadata processing is queued. Evidence: [review report](repair-notes/2026-11-16-entries-76-90/review-report.md). Original owner RM/SQL notes above are retained as the pre-repair observations.

- [x] **80. England NHSBSA prescribing data** (`england_nhsbsa_prescribing_data`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/england_nhsbsa_prescribing_data/` (provider originals); `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=england_nhsbsa_prescribing_data/` (committed row batches).
  Current collection state: **enabled** — daily/historical capture and metadata queues checked on 16 November 2026  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` across 1 failed attempt(s).  
  Current raw processing: Replaced catalogue-only input with native, full-field prescribing rows. Daily collection prefers the current SNOMED catalogue, whose latest probed release is August 2026; the retired catalogue remains available for older months. Verified 1,000 January-2016 rows and 1,000 August-2026 rows. Pagination continues; neither month nor the full history is claimed complete.  
  Athena SQL (bounded published sample, not a source total): `SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'england_nhsbsa_prescribing_data' AND contract_version = '2.0.3' AND job_id IN ('01e15bfae93a53f2eaf2edaad8dba27d1d9fc9edef8d948c56981969fb7a05bf', '0284438d4829006f6ec019be12bdd7317d172cd0e20351d9f3eba4cfc34964b5', '038303d3f9d1403ddd244ad8a490b98519f6f85bf7b3d244ff5576ba15f244b8', '05c01b2c9f684c9b24c136aa9761cbfe2a1a5aae3b8311cacef739cf3487e0a3', '0da7408f9c038518577228312c0a5cd89dbb72497f0bc02ee252fdc975c3f08c') GROUP BY source_key, dataset;`

  RM: no S3 folder
  SQL: no

  Review (16 November 2026): **reviewed** — 160 complete published sample rows. Replaced catalogue-only input with native, full-field prescribing rows. Daily collection prefers the current SNOMED catalogue, whose latest probed release is August 2026; the retired catalogue remains available for older months. Verified 1,000 January-2016 rows and 1,000 August-2026 rows. Pagination continues; neither month nor the full history is claimed complete. Evidence: [review report](repair-notes/2026-11-16-entries-76-90/review-report.md). Original owner RM/SQL notes above are retained as the pre-repair observations.

- [x] **81. Decodo shared web retrieval (access layer)** (`decodo_shared_web_retrieval_access_layer`)  
  Raw S3: Not applicable — retrieval access layer; originals belong to dependent sources.
  Current collection state: **access_layer** — verified through dependent-source retrieval; no standalone queue  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Reviewed as an access layer: successful CDA-AMC retrieval and strict base64-PDF recovery verified the gateway. Standalone raw folders and source_observations rows are not applicable; dependent sources own their original artifacts and observations.  
  Athena SQL (bounded published sample, not a source total): `-- Decodo is a retrieval access layer; standalone source rows are not applicable.`

  Review (16 November 2026): **reviewed** — N/A (access layer). Reviewed as an access layer: successful CDA-AMC retrieval and strict base64-PDF recovery verified the gateway. Standalone raw folders and source_observations rows are not applicable; dependent sources own their original artifacts and observations. Evidence: [review report](repair-notes/2026-11-16-entries-76-90/review-report.md). Original owner RM/SQL notes above are retained as the pre-repair observations.

- [x] **82. SIA / WSTS public semiconductor sales** (`sia_wsts_public_semiconductor_sales`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/sia_wsts_public_semiconductor_sales/`
  Current collection state: **enabled** — daily/historical capture and metadata queues checked on 16 November 2026  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 6 failed attempt(s).  
  Current raw processing: Located and verified the complete saved WSTS billings PDF and restored scoped native-file publication. The old August URL now returns 404, while its archived original remains intact; current daily and historical index discovery completed without download failures.  
  Athena SQL (bounded published sample, not a source total): `SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'sia_wsts_public_semiconductor_sales' AND contract_version = '2.0.3' AND job_id IN ('eb06a5d04d093727576a87a96813262a26d2968aefdd4acab1b9c62e1c26b614') GROUP BY source_key, dataset;`

  RM: no S3 folder
  SQL: yes

  Review (16 November 2026): **reviewed** — 1 complete published sample rows. Located and verified the complete saved WSTS billings PDF and restored scoped native-file publication. The old August URL now returns 404, while its archived original remains intact; current daily and historical index discovery completed without download failures. Evidence: [review report](repair-notes/2026-11-16-entries-76-90/review-report.md). Original owner RM/SQL notes above are retained as the pre-repair observations.

- [x] **83. SEMI worldwide equipment billings** (`semi_worldwide_equipment_billings`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/semi_worldwide_equipment_billings/`
  Current collection state: **enabled** — daily/historical capture and metadata queues checked on 16 November 2026  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Moved discovery to the working official SEAJ index and followed only its worldwide SEMS rows, excluding Japan-only and FPD rows. The joint SEMI/SEAJ worldwide PDFs and back-number PDF are captured; daily and historical crawls are healthy. Paid detailed WWSEMS products are excluded.  
  Athena SQL (bounded published sample, not a source total): `SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'semi_worldwide_equipment_billings' AND contract_version = '2.0.3' AND job_id IN ('493af9a0638ac3d7a5ef1148d0d602944c305bdb063c45d5183468f0070906d4') GROUP BY source_key, dataset;`

  RM: no S3 folder
  SQL: no

  Review (16 November 2026): **reviewed** — 1 complete published sample rows. Moved discovery to the working official SEAJ index and followed only its worldwide SEMS rows, excluding Japan-only and FPD rows. The joint SEMI/SEAJ worldwide PDFs and back-number PDF are captured; daily and historical crawls are healthy. Paid detailed WWSEMS products are excluded. Evidence: [review report](repair-notes/2026-11-16-entries-76-90/review-report.md). Original owner RM/SQL notes above are retained as the pre-repair observations.

- [x] **84. International Federation of Robotics World Robotics** (`international_federation_of_robotics_world_robotics`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/international_federation_of_robotics_world_robotics/`
  Current collection state: **enabled** — daily/historical capture and metadata queues checked on 16 November 2026  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record`; `public_capture_is_discovery_page_only` across 18 failed attempt(s).  
  Current raw processing: Rejected images and discovery pages as reports; verified the complete public 2025 World Robotics executive-summary PDF and published its native-file metadata. Daily and historical discovery continue. This does not assert a paid full database or that the 2025 summary is a 2026 release.  
  Athena SQL (bounded published sample, not a source total): `SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'international_federation_of_robotics_world_robotics' AND contract_version = '2.0.3' AND job_id IN ('b956eb4b673a4546ebd03266e4cf32bc5697a85343379433826835297d7e384a') GROUP BY source_key, dataset;`

  RM: no S3 folder
  SQL: yes

  Review (16 November 2026): **reviewed** — 1 complete published sample rows. Rejected images and discovery pages as reports; verified the complete public 2025 World Robotics executive-summary PDF and published its native-file metadata. Daily and historical discovery continue. This does not assert a paid full database or that the 2025 summary is a 2026 release. Evidence: [review report](repair-notes/2026-11-16-entries-76-90/review-report.md). Original owner RM/SQL notes above are retained as the pre-repair observations.

- [x] **85. IEA-PVPS solar deployment reports** (`iea_pvps_solar_deployment_reports`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/iea_pvps_solar_deployment_reports/`
  Current collection state: **enabled** — daily/historical capture and metadata queues checked on 16 November 2026  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 10 failed attempt(s).  
  Current raw processing: Verified the actual Snapshot of Global PV Markets 2026 PDF, excluded unrelated technical files, and replaced the broken trends index with the working publications index. Daily and historical capture are healthy; additional public reports continue through the queue.  
  Athena SQL (bounded published sample, not a source total): `SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'iea_pvps_solar_deployment_reports' AND contract_version = '2.0.3' AND job_id IN ('97fb4e95091dde3f22dba4e0a8358fa9780738d1a31bda54e4374cf51ed2b06b') GROUP BY source_key, dataset;`

  RM: no S3 folder
  SQL: yes

  Review (16 November 2026): **reviewed** — 1 complete published sample rows. Verified the actual Snapshot of Global PV Markets 2026 PDF, excluded unrelated technical files, and replaced the broken trends index with the working publications index. Daily and historical capture are healthy; additional public reports continue through the queue. Evidence: [review report](repair-notes/2026-11-16-entries-76-90/review-report.md). Original owner RM/SQL notes above are retained as the pre-repair observations.

- [x] **86. Germany G-BA drug benefit assessments** (`germany_g_ba_drug_benefit_assessments`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/germany_g_ba_drug_benefit_assessments/`
  Current collection state: **enabled** — daily/historical capture and metadata queues checked on 16 November 2026  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Restricted discovery to benefit-assessment cases and original dossier/assessment PDFs. Verified an original IQWiG/G-BA benefit-assessment PDF and its published metadata. Daily and historical discovery continue; no clinical or reimbursement interpretation is inferred.  
  Athena SQL (bounded published sample, not a source total): `SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'germany_g_ba_drug_benefit_assessments' AND contract_version = '2.0.3' AND job_id IN ('b0c60b7e25484fc3bea15927f58fe66d94210f673af49293e37af116484f4b40') GROUP BY source_key, dataset;`

  RM: no S3 folder
  SQL: no

  Review (16 November 2026): **reviewed** — 1 complete published sample rows. Restricted discovery to benefit-assessment cases and original dossier/assessment PDFs. Verified an original IQWiG/G-BA benefit-assessment PDF and its published metadata. Daily and historical discovery continue; no clinical or reimbursement interpretation is inferred. Evidence: [review report](repair-notes/2026-11-16-entries-76-90/review-report.md). Original owner RM/SQL notes above are retained as the pre-repair observations.

- [x] **87. France HAS medicine assessment opinions** (`france_has_medicine_assessment_opinions`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/france_has_medicine_assessment_opinions/`
  Current collection state: **enabled** — daily/historical capture and metadata queues checked on 16 November 2026  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Fixed HAS relative links, native CP1252/dollar-quoted CSV validation, and its headerless CT-to-opinion URL export. SMR/ASMR originals and a final committee-opinion PDF are verified and published. All daily download errors recovered. Discovered 10,490 opinion links and restored about 5,000 within the existing frontier cap; historical processing is active and full coverage remains open.  
  Athena SQL (bounded published sample, not a source total): `SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'france_has_medicine_assessment_opinions' AND contract_version = '2.0.3' AND job_id IN ('451cbaabfed1ccc9296116b5b9d0648060021271e1d891adcb1d2d19c3a29ae9', '6bad4a342934cb2ae660edf143542bec0d92d88619aee3f2871676debf5017d3', 'dc312d7a3bfd9e272c25fbde42c02148820a478ca6186ae0ce0607d7ae3644c6', 'de55a7825bfec23ad5d44a27d9da52c2bc7261aad15e8d7615d5490d27efd797', 'e8115c9f77af2b551a5d76b239017a447d8d8f00352daa3049df0879cfeb9078') GROUP BY source_key, dataset;`

  RM: no S3 folder
  SQL: no

  Review (16 November 2026): **reviewed** — 5 complete published sample rows. Fixed HAS relative links, native CP1252/dollar-quoted CSV validation, and its headerless CT-to-opinion URL export. SMR/ASMR originals and a final committee-opinion PDF are verified and published. All daily download errors recovered. Discovered 10,490 opinion links and restored about 5,000 within the existing frontier cap; historical processing is active and full coverage remains open. Evidence: [review report](repair-notes/2026-11-16-entries-76-90/review-report.md). Original owner RM/SQL notes above are retained as the pre-repair observations.

- [ ] **88. NICE technology appraisals** (`nice_technology_appraisals`)  
  Raw S3: Owner paused; retained evidence only. No new raw material acquired.
  Current collection state: **owner_paused** — deliberate pause preserved  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Deliberate owner pause preserved. NICE capture and AI processing were not resumed and no fresh provider request was made. The existing licensed API, cybersecurity review and owner authorization requirements remain; no completed review is claimed.  
  Athena SQL (bounded published sample, not a source total): `SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'nice_technology_appraisals' GROUP BY source_key, dataset;`

  RM: no S3 folder
  SQL: no

  Review (16 November 2026): **not reviewed — intentionally paused** — not run (owner paused). Deliberate owner pause preserved. NICE capture and AI processing were not resumed and no fresh provider request was made. The existing licensed API, cybersecurity review and owner authorization requirements remain; no completed review is claimed. Evidence: [review report](repair-notes/2026-11-16-entries-76-90/review-report.md). Original owner RM/SQL notes above are retained as the pre-repair observations.

- [x] **89. Canada CDA-AMC / CADTH reimbursement reviews** (`canada_cda_amc_cadth_reimbursement_reviews`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/canada_cda_amc_cadth_reimbursement_reviews/`
  Current collection state: **enabled** — daily/historical capture and metadata queues checked on 16 November 2026  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Fixed gateway base64 PDFs that had been mislabelled HTML, preserving the original gateway wrapper separately. Verified and published a final CDA-AMC reimbursement recommendation PDF as well as the separately labelled patient/clinician input. Daily and historical public-file crawls completed their current frontiers; exhaustive review history and clinical interpretation are not asserted.  
  Athena SQL (bounded published sample, not a source total): `SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'canada_cda_amc_cadth_reimbursement_reviews' AND contract_version = '2.0.3' AND job_id IN ('2e31bf1b92a6f506cc9ac059c6dd7bbe3f9ecbead040324ac9e6f645aac9542c', '7cffc150b76ee4c1805246957e707049b0068ae3c4c67d1861d9b2e92bd1577d') GROUP BY source_key, dataset;`

  RM: no S3 folder
  SQL: no

  Review (16 November 2026): **reviewed** — 2 complete published sample rows. Fixed gateway base64 PDFs that had been mislabelled HTML, preserving the original gateway wrapper separately. Verified and published a final CDA-AMC reimbursement recommendation PDF as well as the separately labelled patient/clinician input. Daily and historical public-file crawls completed their current frontiers; exhaustive review history and clinical interpretation are not asserted. Evidence: [review report](repair-notes/2026-11-16-entries-76-90/review-report.md). Original owner RM/SQL notes above are retained as the pre-repair observations.

- [x] **90. France Assurance Maladie Open Medic** (`france_assurance_maladie_open_medic`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/france_assurance_maladie_open_medic/`
  Current collection state: **enabled** — daily/historical capture and metadata queues checked on 16 November 2026  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Corrected the provider download host, catalogue/document classification and fresh public download-link resolution. Verified the complete 2025 Open Medic ZIP, checksum and every member CRC. Daily and historical capture are active. SQL rows represent validated original annual dataset files; individual medicine/cost-row extraction is a separate downstream step.  
  Athena SQL (bounded published sample, not a source total): `SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'france_assurance_maladie_open_medic' AND contract_version = '2.0.3' AND job_id IN ('d19394d3b1f339cff55f60225b27ab76f369093a835d297d4eb043ec8ba642c9') GROUP BY source_key, dataset;`

  RM: no S3 folder
  SQL: no

### Day 7 — Tuesday — 17 November 2026 (15 catalog entries)

  Review (16 November 2026): **reviewed** — 1 complete published sample rows. Corrected the provider download host, catalogue/document classification and fresh public download-link resolution. Verified the complete 2025 Open Medic ZIP, checksum and every member CRC. Daily and historical capture are active. SQL rows represent validated original annual dataset files; individual medicine/cost-row extraction is a separate downstream step. Evidence: [review report](repair-notes/2026-11-16-entries-76-90/review-report.md). Original owner RM/SQL notes above are retained as the pre-repair observations.

- [x] **91. Japan MHLW NDB Open Data** (`japan_mhlw_ndb_open_data`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/japan_mhlw_ndb_open_data/` (original provider files; verified object links below).  
  Current collection state: **enabled — daily and historical capture verified; metadata source enabled**.
  Pre-repair recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'japan_mhlw_ndb_open_data' AND contract_version = '2.0.3' GROUP BY source_key;`

  Owner's pre-repair check:

  RM: no S3 bucket
  SQL: no

  Review (18 November 2026): **reviewed** — Current RM: yes; SQL: yes. The collector followed NDB discovery pages without selecting native workbooks. A complete official XLSX is now archived; ZIP member CRCs, four worksheets and worksheet XML passed the bounded sample check. Verified Athena sample: 1 complete row(s). SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Daily and historical checkpoints are verified for the declared scope; complete historical coverage remains under audit. Verified original: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/japan_mhlw_ndb_open_data/4ac58c59d85810592d5ab33f2d980e6f75907e650dffdd88644d82c490665f13`. Evidence and scope: [review status](repair-notes/2026-11-18-entries-91-105/review-status.json). Original owner RM/SQL notes are retained as pre-repair observations.

- [x] **92. CNINFO mainland-China company disclosures** (`cninfo_mainland_china_company_disclosures`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/cninfo_mainland_china_company_disclosures/` (original provider files; verified object links below).  
  Current collection state: **enabled — daily and historical capture verified; metadata source enabled**.
  Pre-repair recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Complete native filing-index row paired with its original PDF/XML document; no XBRL fact extraction or historical-vintage inference.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'cninfo_mainland_china_company_disclosures' AND contract_version = '2.0.3' GROUP BY source_key;`

  Owner's pre-repair check:

  RM: no S3 bucket
  SQL: no

  Review (18 November 2026): **reviewed** — Current RM: yes; SQL: yes. The homepage is a JavaScript discovery page; the announcement endpoint requires POST. The new collector pairs complete native index rows with original PDFs. One seven-page PDF and its native index row passed sample validation. Verified Athena sample: 8 complete row(s). Complete native filing-index row paired with its original PDF/XML document; no XBRL fact extraction or historical-vintage inference. Daily and historical checkpoints are verified for the declared scope; complete historical coverage remains under audit. Verified original: `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/cninfo_mainland_china_company_disclosures/11f041a2c1ecd7cf1361e42c60936ba3ea524c5e40bad7d48f59fe9c1c13c5ba`. Evidence and scope: [review status](repair-notes/2026-11-18-entries-91-105/review-status.json). Original owner RM/SQL notes are retained as pre-repair observations.

- [x] **93. China NBS industrial production** (`china_nbs_industrial_production`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/china_nbs_industrial_production/` (original provider files; verified object links below).  
  Current collection state: **enabled — daily and historical capture verified; metadata source enabled**.
  Pre-repair recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'china_nbs_industrial_production' AND contract_version = '2.0.3' GROUP BY source_key;`

  Owner's pre-repair check:

  RM: no S3 bucket
  SQL: no

  Review (18 November 2026): **reviewed** — Current RM: yes; SQL: yes. The original statistical HTML releases were misclassified as discovery pages. The repair preserves substantive releases and all same-directory figures. An October 2026 release and nine original figures are archived. Verified Athena sample: 1 complete row(s). SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Daily and historical checkpoints are verified for the declared scope; complete historical coverage remains under audit. Verified original: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/china_nbs_industrial_production/2c2bd73a2beea328928d9fced2365d280e32b17af5e51e310f5762cbc9ca8745`. Evidence and scope: [review status](repair-notes/2026-11-18-entries-91-105/review-status.json). Original owner RM/SQL notes are retained as pre-repair observations.

- [x] **94. China MIIT electronics and battery statistics** (`china_miit_electronics_and_battery_statistics`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/china_miit_electronics_and_battery_statistics/` (original provider files; verified object links below).  
  Current collection state: **enabled — daily and historical capture verified; metadata source enabled**.
  Pre-repair recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'china_miit_electronics_and_battery_statistics' AND contract_version = '2.0.3' GROUP BY source_key;`

  Owner's pre-repair check:

  RM: no S3 bucket
  SQL: yes

  Review (18 November 2026): **reviewed** — Current RM: yes; SQL: yes. The old route followed navigation and unrelated binary assets. The deployed scope selects original MIIT electronics/battery statistical releases. A native January–August 2026 release is archived. Verified Athena sample: 1 complete row(s). SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Daily and historical checkpoints are verified for the declared scope; complete historical coverage remains under audit. Verified original: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/china_miit_electronics_and_battery_statistics/2562c45c918c98fcad8aa4192637b68b3cf963c2155a7e2c7734b9d4e5806aaf`. Evidence and scope: [review status](repair-notes/2026-11-18-entries-91-105/review-status.json). Original owner RM/SQL notes are retained as pre-repair observations.

- [x] **95. China NEA power statistics** (`china_nea_power_statistics`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/china_nea_power_statistics/` (original provider files; verified object links below).  
  Current collection state: **enabled — daily and historical capture verified; metadata source enabled**.
  Pre-repair recorded raw-data errors: `public_capture_is_discovery_page_only` across 5 failed attempt(s).  
  Current raw processing: SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'china_nea_power_statistics' AND contract_version = '2.0.3' GROUP BY source_key;`

  Owner's pre-repair check:

  RM: no S3 bucket
  SQL: yes

  Review (18 November 2026): **reviewed** — Current RM: yes; SQL: yes. Genuine short statistical releases were treated as discovery-only pages. The validator accepts the complete official release and requires its original table figure. Both are archived; the PNG passed CRC/structure checks. Verified Athena sample: 1 complete row(s). SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Daily and historical checkpoints are verified for the declared scope; complete historical coverage remains under audit. Verified original: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/china_nea_power_statistics/3d45ee768c1e429a439cef99cd812ca3a9b0572d1bc0795e9c7ddab948103b21`. Evidence and scope: [review status](repair-notes/2026-11-18-entries-91-105/review-status.json). Original owner RM/SQL notes are retained as pre-repair observations.

- [x] **96. China NHSA reimbursement and procurement** (`china_nhsa_reimbursement_and_procurement`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/china_nhsa_reimbursement_and_procurement/` (original provider files; verified object links below).  
  Current collection state: **enabled — daily and historical capture verified; metadata source enabled**.
  Pre-repair recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'china_nhsa_reimbursement_and_procurement' AND contract_version = '2.0.3' GROUP BY source_key;`

  Owner's pre-repair check:

  RM: no S3 bucket
  SQL: no

  Review (18 November 2026): **reviewed** — Current RM: yes; SQL: yes. The old route crawled navigation, misclassified substantive notices and delayed every transient failure for 24 hours. Discovery now follows the relevant policy index; a source-specific transient retry and 15-minute backoff are installed. The native catalogue notice and both linked original PDFs passed worker validation and publication; the final daily checkpoint has zero current failures. Verified Athena sample: 3 complete row(s). SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Daily and historical checkpoints are verified for the declared scope; complete historical coverage remains under audit. Verified original: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/china_nhsa_reimbursement_and_procurement/cc52976c8a25f90c623febddc6bd973830e63768c8e6d188e96fdb632840fb06`. Evidence and scope: [review status](repair-notes/2026-11-18-entries-91-105/review-status.json). Original owner RM/SQL notes are retained as pre-repair observations.

- [x] **97. China MOFCOM export controls** (`china_mofcom_export_controls`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/china_mofcom_export_controls/` (original provider files; verified object links below).  
  Current collection state: **enabled — daily and historical capture verified; metadata source enabled**.
  Pre-repair recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'china_mofcom_export_controls' AND contract_version = '2.0.3' GROUP BY source_key;`

  Owner's pre-repair check:

  RM: no S3 bucket
  SQL: no

  Review (18 November 2026): **reviewed** — Current RM: yes; SQL: yes. The former route archived a navigation-heavy export-control page rather than a formal notice. The staged parser rejects generic site titles and uses a substantive official MOFCOM notice. One complete notice is archived. Verified Athena sample: 1 complete row(s). SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Daily and historical checkpoints are verified for the declared scope; complete historical coverage remains under audit. Verified original: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/china_mofcom_export_controls/70ab2e80822b0c3a6ea469e6c18c04244090ad5aea0da1c3152d148337ebcc44`. Evidence and scope: [review status](repair-notes/2026-11-18-entries-91-105/review-status.json). Original owner RM/SQL notes are retained as pre-repair observations.

- [ ] **98. South Korea FSS OpenDART** (`south_korea_fss_opendart`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/south_korea_fss_opendart/` (original provider files; verified object links below).  
  Current collection state: **enabled — daily and historical capture verified; metadata source enabled** — individual provider-document gaps remain isolated.
  Pre-repair recorded raw-data errors: `missing_verified_raw_artifacts:primary_document` across 4 failed attempt(s).  
  Current raw processing: Complete native filing-index row paired with its original PDF/XML document; no XBRL fact extraction or historical-vintage inference.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'south_korea_fss_opendart' AND contract_version = '2.0.3' GROUP BY source_key;`

  Owner's pre-repair check:

  RM: yes
  SQL: no

  Review (18 November 2026): **partially reviewed — provider document gaps** — Current RM: partial; SQL: yes. The collector previously archived only listing rows. Native receipt-specific original ZIP capture is repaired, and both daily and historical commits plus four complete filing records passed metadata/Athena verification. Four proof batches remain rejected for unavailable or malformed provider originals, and processing retains these gaps explicitly. An additional archived sample contains malformed XML. The source stays enabled with failures isolated by source/date; its review remains partial. Verified Athena sample: 4 complete row(s). Complete native filing-index row paired with its original PDF/XML document; no XBRL fact extraction or historical-vintage inference. Daily and historical checkpoints are verified for the declared scope; complete historical coverage remains under audit. Verified original: `s3://data-collection-059416028963-us-east-1-an/research-data/source_documents/south_korea_fss_opendart/723fbe38f4f4d06e59a1ab1806845a2cb3de1142b4afe2112b70f89f9b248a49`. Evidence and scope: [review status](repair-notes/2026-11-18-entries-91-105/review-status.json). Original owner RM/SQL notes are retained as pre-repair observations.

- [ ] **99. South Korea KOSIS statistical OpenAPI** (`south_korea_kosis_statistical_openapi`)  
  Raw S3: **not created — no configured collector**
  Current collection state: **blocked — missing KOSIS key and table plan**. The registry enabled flag does not represent a working collector.
  Pre-repair recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'south_korea_kosis_statistical_openapi' GROUP BY source_key;`

  Owner's pre-repair check:

  RM: no S3 bucket
  SQL: no

  Review (18 November 2026): **not reviewed — owner configuration required** — Current RM: no; SQL: no. The enabled registry flag was misleading: there is no collector plan, historical route, metadata job inventory or configured KOSIS credential. Owner action: obtain an issued KOSIS OpenAPI key, add it as field kosis to the existing dataSourceAPIkeys-PSTzff secret without replacing other fields, and identify the intended tables/indicators. Do not paste the key into chat.Evidence and scope: [review status](repair-notes/2026-11-18-entries-91-105/review-status.json). Original owner RM/SQL notes are retained as pre-repair observations.

- [x] **100. Taiwan TWSE/MOPS issuer and revenue archives** (`taiwan_twse_mops_issuer_and_revenue_archives`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/taiwan_twse_mops_issuer_and_revenue_archives/` (original provider files; verified object links below).  
  Current collection state: **enabled — daily and historical capture verified; metadata source enabled**.
  Pre-repair recorded raw-data errors: `missing_verified_raw_artifacts:primary_document` across 2 failed attempt(s).  
  Current raw processing: Native issuer/revenue rows with all returned fields and original reporting month/units. Both complete source arrays (2190 rows) passed raw verification; published proof samples cover 64 rows and continuation remains active. Historical MOPS issuer and monthly-release archive coverage remains unverified.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'taiwan_twse_mops_issuer_and_revenue_archives' AND contract_version = '2.0.3' GROUP BY source_key;`

  Owner's pre-repair check:

  RM: no S3 bucket
  SQL: no

  Review (18 November 2026): **reviewed** — Current RM: yes; SQL: yes. The native issuer/revenue JSON arrays were wrongly treated as filings that required a primary PDF. Two complete native TWSE arrays are archived. The deployed converter retains every original row, company identifier, ROC reporting month and native units. These are current snapshots, not a full MOPS historical filing archive. Verified Athena sample: 64 complete row(s). Native issuer/revenue rows with all returned fields and original reporting month/units. Both complete source arrays (2190 rows) passed raw verification; published proof samples cover 64 rows and continuation remains active. Historical MOPS issuer and monthly-release archive coverage remains unverified. Daily and historical checkpoints are verified for the declared scope; complete historical coverage remains under audit. Verified original: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/taiwan_twse_mops_issuer_and_revenue_archives/d723b8f56406a38101dc1c23780a93188f39bfeb9c8d8556b9ba3def2eeeef5e`. Evidence and scope: [review status](repair-notes/2026-11-18-entries-91-105/review-status.json). Original owner RM/SQL notes are retained as pre-repair observations.

- [x] **101. Taiwan customs trade statistics** (`taiwan_customs_trade_statistics`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/taiwan_customs_trade_statistics/` (original provider files; verified object links below).  
  Current collection state: **enabled — daily and historical capture verified; metadata source enabled**.
  Pre-repair recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Native monthly aggregate clearance rows, with reporting year and NTD-thousand fields retained. All 153 source rows passed raw verification; published proof sample covers 32 rows, with continuation active. Detailed HS/country trade is outside this feed.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'taiwan_customs_trade_statistics' AND contract_version = '2.0.3' GROUP BY source_key;`

  Owner's pre-repair check:

  RM: no S3 bucket
  SQL: no

  Review (18 November 2026): **reviewed** — Current RM: yes; SQL: yes. The route crawled the interactive customs website instead of the official public CSV. The complete monthly aggregate clearance CSV is archived. The deployed converter preserves native year/month and NTD-thousand fields; this is not detailed HS/country trade. Verified Athena sample: 32 complete row(s). Native monthly aggregate clearance rows, with reporting year and NTD-thousand fields retained. All 153 source rows passed raw verification; published proof sample covers 32 rows, with continuation active. Detailed HS/country trade is outside this feed. Daily and historical checkpoints are verified for the declared scope; complete historical coverage remains under audit. Verified original: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/taiwan_customs_trade_statistics/052826a293ba16b0199fee8bac00990e6313852aa9517feea583573ce3fff8ae`. Evidence and scope: [review status](repair-notes/2026-11-18-entries-91-105/review-status.json). Original owner RM/SQL notes are retained as pre-repair observations.

- [x] **102. India IBM mineral production** (`india_ibm_mineral_production`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/india_ibm_mineral_production/` (original provider files; verified object links below).  
  Current collection state: **enabled — daily and historical capture verified; metadata source enabled**.
  Pre-repair recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'india_ibm_mineral_production' AND contract_version = '2.0.3' GROUP BY source_key;`

  Owner's pre-repair check:

  RM: no S3 bucket
  SQL: no

  Review (18 November 2026): **reviewed** — Current RM: yes; SQL: yes. The old homepage crawl did not follow monthly mineral-production report files. The June 2026 original PDF is archived. A bounded archive plan is prepared; older year index URLs and monthly completeness still need worker checks. Verified Athena sample: 1 complete row(s). SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Daily and historical checkpoints are verified for the declared scope; complete historical coverage remains under audit. Verified original: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/india_ibm_mineral_production/33a965aa326ff927cfdb790a5e9d0a0aa7f19d0c7fd50e4ac0a4540708ca8ba0`. Evidence and scope: [review status](repair-notes/2026-11-18-entries-91-105/review-status.json). Original owner RM/SQL notes are retained as pre-repair observations.

- [x] **103. Indonesia ESDM and Geological Agency mineral statistics** (`indonesia_esdm_and_geological_agency_mineral_statistics`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/indonesia_esdm_and_geological_agency_mineral_statistics/` (original provider files; verified object links below).  
  Current collection state: **enabled — daily and historical capture verified; metadata source enabled**.
  Pre-repair recorded raw-data errors: `missing_verified_raw_artifacts:provider_record`; `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'indonesia_esdm_and_geological_agency_mineral_statistics' AND contract_version = '2.0.3' GROUP BY source_key;`

  Owner's pre-repair check:

  RM: no S3 bucket
  SQL: yes

  Review (18 November 2026): **reviewed** — Current RM: yes; SQL: yes. Legacy accepted site JPEGs were unrelated to mineral statistics. The corrected route follows Geological Agency mineral/coal resource-and-reserve reports; a complete official original report passed PDF validation and publication. All 117 individually confirmed invalid legacy jobs were superseded, with published partitions withdrawn and originals retained. Verified Athena sample: 1 complete row(s). SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Daily and historical checkpoints are verified for the declared scope; complete historical coverage remains under audit. Verified original: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/indonesia_esdm_and_geological_agency_mineral_statistics/bef74715b45ac017454d8171d81a6e8c7019362d4c31393d584de1af0d5e751c`. Evidence and scope: [review status](repair-notes/2026-11-18-entries-91-105/review-status.json). Original owner RM/SQL notes are retained as pre-repair observations.

- [x] **104. Brazil ANM mineral yearbook** (`brazil_anm_mineral_yearbook`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/brazil_anm_mineral_yearbook/` (original provider files; verified object links below).  
  Current collection state: **enabled — daily and historical capture verified; metadata source enabled**.
  Pre-repair recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'brazil_anm_mineral_yearbook' AND contract_version = '2.0.3' GROUP BY source_key;`

  Owner's pre-repair check:

  RM: no S3 bucket
  SQL: no

  Review (18 November 2026): **reviewed** — Current RM: yes; SQL: yes. ANM moved its public data host, its TLS response omitted an intermediate certificate, and native CSVs use CP1252. The provider-specific intermediate chain was independently verified to trusted roots, without disabling TLS checks. All three native production CSVs were captured, fully parsed and published. Verified Athena sample: 3 complete row(s). SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Daily and historical checkpoints are verified for the declared scope; complete historical coverage remains under audit. Verified original: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/brazil_anm_mineral_yearbook/0f64e7a38965d0bc9cf63a891ba9e19ab361e8b5109b2926b660fdc67a894539`. Evidence and scope: [review status](repair-notes/2026-11-18-entries-91-105/review-status.json). Original owner RM/SQL notes are retained as pre-repair observations.

- [x] **105. Brazil ANM CFEM mining royalties** (`brazil_anm_cfem_mining_royalties`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/brazil_anm_cfem_mining_royalties/` (original provider files; verified object links below).  
  Current collection state: **enabled — daily and historical capture verified; metadata source enabled**.
  Pre-repair recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'brazil_anm_cfem_mining_royalties' AND contract_version = '2.0.3' GROUP BY source_key;`

  Owner's pre-repair check:

  RM: no S3 bucket
  SQL: yes

  Review (18 November 2026): **reviewed** — Current RM: yes; SQL: yes. The legacy route accepted an unrelated protocol manual. It now uses three official CFEM revenue CSV chunks, each within the 128 MB capture limit, with verified TLS and native encoding. Entire chunks passed CSV/schema/checksum checks and publication. All 101 individually confirmed bad legacy jobs were superseded; published partitions were withdrawn and raw objects retained. Verified Athena sample: 3 complete row(s). SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Daily and historical checkpoints are verified for the declared scope; complete historical coverage remains under audit. Verified original: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/brazil_anm_cfem_mining_royalties/bff3919f6da4f23d7c08ba53f6bca7812e30252f79856de7185e2d88903dcfb7`. Evidence and scope: [review status](repair-notes/2026-11-18-entries-91-105/review-status.json). Original owner RM/SQL notes are retained as pre-repair observations.

### Day 8 — Wednesday — 18 November 2026 (15 catalog entries)

- [ ] **106. Brazil MDIC Comex Stat API** (`brazil_mdic_comex_stat_api`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=brazil_mdic_comex_stat_api/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'brazil_mdic_comex_stat_api' GROUP BY source_key;`

  RM: no S3 bucket
  SQL: no

- [ ] **107. Chile COCHILCO production and mining economics** (`chile_cochilco_production_and_mining_economics`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=chile_cochilco_production_and_mining_economics/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'chile_cochilco_production_and_mining_economics' GROUP BY source_key;`

RM: no S3 bucket
SQL: no

- [ ] **108. Chile SERNAGEOMIN mining yearbooks** (`chile_sernageomin_mining_yearbooks`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=chile_sernageomin_mining_yearbooks/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'chile_sernageomin_mining_yearbooks' GROUP BY source_key;`

  RM: no S3 bucket
  SQL: no

- [ ] **109. Chile SMA SNIFA environmental compliance** (`chile_sma_snifa_environmental_compliance`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=chile_sma_snifa_environmental_compliance/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'chile_sma_snifa_environmental_compliance' GROUP BY source_key;`

  RM: no S3 bucket
  SQL: no

- [ ] **110. Peru MINEM mining bulletins and yearbooks** (`peru_minem_mining_bulletins_and_yearbooks`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=peru_minem_mining_bulletins_and_yearbooks/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 4 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'peru_minem_mining_bulletins_and_yearbooks' GROUP BY source_key;`

  RM: no S3 bucket
  SQL: no

- [ ] **111. Argentina SIACAM mining indicators** (`argentina_siacam_mining_indicators`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=argentina_siacam_mining_indicators/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'argentina_siacam_mining_indicators' GROUP BY source_key;`

  RM: no S3 bucket
  SQL: no

- [ ] **112. Brazil ANM SIGMINE and Cadastro Mineiro** (`brazil_anm_sigmine_and_cadastro_mineiro`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=brazil_anm_sigmine_and_cadastro_mineiro/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 1 failed attempt(s).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'brazil_anm_sigmine_and_cadastro_mineiro' GROUP BY source_key;`

  RM: no S3 bucket
  SQL: no

- [ ] **113. Peru INGEMMET GEOCATMIN** (`peru_ingemmet_geocatmin`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=peru_ingemmet_geocatmin/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'peru_ingemmet_geocatmin' GROUP BY source_key;`

  RM: no S3 bucket
  SQL: no

- [ ] **114. ImportYeti shipment and supplier relationships** (`importyeti_shipment_and_supplier_relationships`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=importyeti_shipment_and_supplier_relationships/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'importyeti_shipment_and_supplier_relationships' GROUP BY source_key;`

  RM: no S3 bucket
  SQL: no

- [ ] **115. ImportGenius international shipments** (`importgenius_international_shipments`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=importgenius_international_shipments/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'importgenius_international_shipments' GROUP BY source_key;`

  RM: no S3 bucket
  SQL: no

- [ ] **116. MarineTraffic historical vessel tracks and port calls** (`marinetraffic_historical_vessel_tracks_and_port_calls`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=marinetraffic_historical_vessel_tracks_and_port_calls/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'marinetraffic_historical_vessel_tracks_and_port_calls' GROUP BY source_key;`

  RM: no S3 bucket
  SQL: no

- [ ] **117. Kpler commodity cargo flows** (`kpler_commodity_cargo_flows`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=kpler_commodity_cargo_flows/`  
  Current collection state: **enabled — not stopped** (no live restriction returned)  
  Recorded raw-data errors: None recorded in the 31 October raw-error inventory.  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'kpler_commodity_cargo_flows' GROUP BY source_key;`

  RM: no S3 bucket
  SQL:

- [ ] **118. US Census International Trade API** (`us_census_international_trade_api`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=us_census_international_trade_api/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `missing_verified_raw_artifacts:provider_record`  
  Recorded raw-data errors: `missing_verified_raw_artifacts:provider_record` (latest live failure only).  
  Current raw processing: Archives native observations with dimensions, units, flags, and timestamps; extracts normalized measurements for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'us_census_international_trade_api' GROUP BY source_key;`

  RM: yes
  SQL:

- [ ] **119. Eurostat Comext goods trade** (`eurostat_comext_goods_trade`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=eurostat_comext_goods_trade/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` across 7 failed attempt(s).  
  Current raw processing: Archives native observations with dimensions, units, flags, and timestamps; extracts normalized measurements for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'eurostat_comext_goods_trade' GROUP BY source_key;`

  RM: no S3 bucket
  SQL"

- [ ] **120. Climate TRACE industrial assets and activity** (`climate_trace_industrial_assets_and_activity`)  
  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=climate_trace_industrial_assets_and_activity/`  
  Current collection state: **raw_stopped** — 4 consecutive raw failures; latest: `public_capture_is_discovery_page_only`  
  Recorded raw-data errors: `public_capture_is_discovery_page_only` (latest live failure only).  
  Current raw processing: Archives the unmodified provider record; extracts source identity, retrieval provenance, and normalized source-record fields for ``.  
  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'climate_trace_industrial_assets_and_activity' GROUP BY source_key;`

  RM: no S3 bucket
  SQL:

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

