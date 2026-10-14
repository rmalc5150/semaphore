September 25 review: source contract tests and fresh bounded Athena queries passed; universe 0.5 and 108 dated admissions are published. Nine people feeds and retrieval 2.1 are active. See SOURCE_END_TO_END_VERIFICATION.md and COMPANY_ADMISSION.md for exact checks, scope and unresolved source/identity gaps. Earlier release notes below are retained as history.

September 24 memory incident: conference publication was stopped, fixed, and subsequently resumed at the user's request. The streaming fix passed a full 98,408-record local curation/read-back benchmark at 216.28 MiB peak process RSS; a 768 MiB service cap is installed. All jobs now run through a shared 2 GB memory envelope. See CONFERENCE_COLLECTION.md and reports/conference-memory-check.json.

September 24 continuation: SEC, regulatory and disclosure recurring Athena publication is enabled and initial partitions verified. DOI proceedings daily/history collection is scheduled; publication has resumed under memory limits. 4,035 daily proceedings observations were verified in Athena. See RESEARCH_PUBLICATION.md and CONFERENCE_COLLECTION.md. Active work is source collection and verification for event reconstruction; specialist implementation and HMM/TFT inputs are deferred. People-source collection and archive retrieval are now scheduled and initial Athena partitions verified (PEOPLE_COLLECTION.md). Broader personnel history, social, additional abstracts, EODHD profile publication coverage and existing source gaps remain outstanding.

September 24 rollout: news automation and market prices/splits/dividends are now implemented and scheduled, with partitioned Athena publication. See NEWS_AUTOMATION.md, MARKET_COLLECTION.md and EODHD_QUOTA.md for current limits and coverage. Older pilot notes below are retained as history.

Scope update: IBKR news is excluded at the user’s request. Legacy files are retained as inactive reference only.

Latest verified source and Athena gap audit: [MIGRATION_AUDIT_2026-09-24.md](MIGRATION_AUDIT_2026-09-24.md). It supersedes older scheduling/coverage status statements below.

September 24 cutover: scheduled global patent backfill now starts 2021-01-01
with separate collection/publication checkpoints and unchanged shared query
budgets. January–April 2015 remain published (164,690 records). All migrated historical
collector defaults now start 2021-01-01, superseding the patent-only cutover. HMM/TFT intended start is 2021-01-01; coverage and
point-in-time eligibility still require validation. See HISTORICAL_COLLECTION.md
and PATENT_BACKFILL_OPERATIONS.md. Earlier activation details below are historical.

# Collector migration tracker

1. Shared universe, entity IDs, sectors and timestamp contract: implemented;
   initial company seed remains provisional.
2. Shared S3/local storage, immutable manifests, resume and watermarks:
   implemented.
3. SEC historical/daily collector and SEC-to-Athena example: live verified.
4. Remaining collectors, in the agreed groups:
   - Clinical/regulatory: seven new shared entry points and all seven sources
     live in Athena. ChiCTR has a complete 93-record daily window. NMPA has one
     verified in-window record from a three-ID cohort. Full NMPA baseline and
     recurring reconciliation remain. See `REGULATORY_COLLECTION.md` for exact coverage.
   - Other corporate disclosures and dependent PR/licensing/M&A collectors:
     new shared historical/daily paths implemented, including document-text
     prerequisites and strategic-transaction candidates. Live HKEX metadata,
     SEC document and candidate runs completed and the Athena pilot is live
     and verified; see DISCLOSURE_COLLECTION.md
     for the bounded Athena example and exact coverage.
   - Patents: shared historical/daily USPTO discovery and global JSONL ingestion
     implemented, with source evidence, checkpoints, shared-universe candidates
     and all agreed storage categories. S3 export inbox created and BigQuery
     connected through AWS federation. Direct bounded global historical queries
     now checkpoint their job/results into S3. The September 23 revision reaches
     CN September 8 and US September 17; country maxima do not prove completeness.
     The hourly global backfill now targets January 2021, with a first
     complete/audited month of 37,738 candidates. See PATENT_BACKFILL_OPERATIONS.md.
     January 2015 is now curated and live verified in four additional monthly
     Athena views: 25,551 publications have supported technology and 958 have
     registry-supported name links; ownership and historical model eligibility
     remain unestablished. Automatic monthly publication is enabled every ten
     minutes with independent retries and durable verification receipts.
     See PATENT_BACKFILL_ATHENA.md.
     The 78,542-record January 2025 sample has a versioned S3 review release:
     54,370 have supported technology, 599 have registry-name links. Official US
     assignment history is validated on 23 applications (29 recorded events).
     A separate top-20 GLEIF review adds five registry entity links covering
     2,860 publications. Universe 0.3 now adds four legal entities and incorporates
     four receipt/underlying relationships while retaining old IDs.
     Fourteen of the new 15 US histories have matching recorded recipient names.
     Nine Athena tables are live and verified: 78,542 publications, 3,459 with
     supported name links, all 23 assignment histories, and four reviewed
     depositary-receipt relationships. Broader shared-universe reconciliation,
     current ownership, identity resolution, global daily coverage and scheduling
     remain. See PATENT_COLLECTION.md, PATENT_REVIEW.md and PATENT_ATHENA.md.
   - News: Finlight/Marketaux shared historical/daily entry points implemented,
     with all four sector queries, English/Chinese Finlight scopes, multilingual
     Marketaux results, bounded requests, evidence and resumable checkpoints.
     September 23 daily cohort: 12 completed search scopes, 1,042 observations;
     four news Athena tables are live verified with 964 provider article records
     and 81 candidate company links (81 tests and three live queries passed).
     Finlight Pro Light cannot provide 2015 history; Marketaux
     returned archive samples for 2021–2026 and completed four sector scopes
     for January 1, 2021 (44 observations); complete archive coverage is unverified.
     Recurring scheduling/publication, historical coverage 
     remain. See NEWS_COLLECTION.md for exact coverage and release status.
   - Market prices and corporate actions: shared EODHD prices/splits/dividends and official HKEX quotation paths implemented; bounded collection and Athena publication timers enabled. Broader action types and complete historical coverage remain.
   - People-source feeds/archive retrieval and DOI proceedings are scheduled; broader personnel history, partnerships, additional abstracts and remaining discovery are incomplete.
   - Historical/daily runners: migrated for the shared SEC, regulatory, HKEX,
     document and event-candidate paths. Per-source S3 progress, dependencies,
     catch-up and reconciliation are implemented; other sources remain explicit
     integration gaps. See COLLECTION_OPERATIONS.md.
5. Broader curated Athena tables and model features: SEC, clinical, disclosure
   and patent pilots exist; eight EODHD research/review tables are live and verified.
   Incremental release updates, larger-scale partitions, identity
   verification and point-in-time HMM/TFT features remain to be implemented.

Company-universe expansion: the reviewed EODHD snapshot contains 9,438 profiles, with 132,346
inventory symbols remaining. Review records 515 supported decisions across 492
listing symbols, 35 rejected matches and 329 needing more evidence. Versioned
universe 0.3.0 contains 498 retained company entries and 492 listings; 105 company
identities are registry-corroborated, 389 remain pending and four receipt-derived
placeholders are rejected/disabled. Seven universe tables and the
expanded research/review tables are live in Athena. A quota-safe daily timer is
enabled for the remaining profile cohorts. See `COMPANY_UNIVERSE.md` and
`EODHD_ATHENA.md` for exact releases, SQL and limitations.
Resumable exchange inventory, manifest-dependent profile scanning, explicit
cross-day resume, quota reserves, coverage reporting and four-sector candidate
rules are implemented. Provider coverage uses exchange inventories plus
individual profiles. The shared
SEC, regulatory and disclosure daily runner routes dates from 2026-09-24 to
universe 0.3.0. Earlier windows, historical defaults and the NMPA baseline keep
0.2.0 and their existing checkpoints. Display-sector membership remains pending
for two new legal entities. See COMPANY_UNIVERSE.md for exact cutover behavior.
Confirmed SEC matches recognize both cik and sec_cik identifiers and still
require a verified identifier and verified legal company. Existing Athena
pilots retain their original snapshots until explicitly republished.

Each collector group should produce shared raw evidence and a reviewable
curated research release. Source-specific failures and unsupported history
must remain explicit rather than being reported as empty successful datasets.
