

## API and site access catalog

The links below are source documentation or official source sites. Endpoint families must be validated against the chosen dataset before implementation; do not infer that a site has a supported public API because its browser makes JSON requests.

| Source | API or site | How to collect / access status | Coverage caveat |
|---|---|---|---|
| A01 SEC | [EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | Public JSON submissions and XBRL; no key. Use identified requests and SEC fair-access rules; archives for filing text | US filers and foreign issuers filing with SEC; custom tags/segments need original filing extraction |
| A02 HKEX | [HKEXnews title search](https://www1.hkexnews.hk/search/titlesearch.xhtml?lang=en) | Existing site adapter can be reused after verifying manifests and permitted access; original announcement PDFs | Hong Kong disclosures; preserve language and source-calendar date; not a promised public API |
| A03 Company/customer/lender sites | Corporate investor-relations, newsroom, product, warranty, careers and supplier pages, selected from verified company domains | RSS/Atom where offered, sitemaps and permitted HTML/PDF downloads; maintain an explicit URL allowlist per company | No single API; deleted pages and vendor claims require snapshots, dates and corroboration |
| A04 EODHD | [API quick start](https://eodhd.com/financial-apis/quick-start-with-our-financial-data-apis), [fundamentals documentation](https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds) | Key/subscription; reuse current quota controller and purchased entitlements | Test exchange, delisted-security and historical fundamental coverage; do not assume all fields are point-in-time |
| A05 Private company funding | [Crunchbase API access FAQ](https://support.crunchbase.com/hc/en-us/articles/32319290128019-Crunchbase-API-FAQ) | Licensed API if available; otherwise disclosed company/investor announcements | API availability does not mean our account has access; incomplete private valuations and deal terms |
| A06 US opportunities | [SAM.gov Get Opportunities API](https://open.gsa.gov/api/get-opportunities-public-api/) | API key; public search, attachment handling and pagination | Opportunity versions/history require specific validation; not equivalent to all state/local procurement |
| A07 EU procurement | [TED Search API](https://docs.ted.europa.eu/api/latest/search.html), [download guidance](https://docs.ted.europa.eu/ODS/latest/reuse/search-api.html) | Search notices and retrieve structured notice documents; validate current endpoint/version | Notice schema, language and procurement scope vary; link corrections and awards |
| A08 US federal awards | [USAspending API](https://api.usaspending.gov/docs/) | Documented public search/detail/download APIs; join award and recipient IDs | Federal award reporting is not a complete private-sector customer dataset |
| A09 Software releases | [GitHub releases API](https://docs.github.com/en/rest/releases/releases) | Public repository release listing; token optional for public reads, quotas depend on authentication | Only repositories demonstrably controlled by the company/project; license governs artifact reuse |
| A10 Public jobs | [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html), [Lever Postings API](https://github.com/lever/postings-api) | Public board/posting GET endpoints for known employer board IDs | Only employers using these platforms; no assumed full historical jobs archive |
| A11 Robotics tests | [NIST performance assessment framework](https://www.nist.gov/programs-projects/performance-assessment-framework-robotic-systems) | Published methods/reports as reference documents; follow linked datasets if applicable | Measurement framework, not universal competitor scores or production uptime |
| A12 AI-chip benchmarks | [MLCommons results](https://docs.mlcommons.org/inference_results_v5.1/), [rules](https://github.com/mlcommons/inference_policies/blob/master/inference_rules.adoc) | Versioned results and linked repositories; ingest original result/configuration files | The linked release is an example, not a claim it is newest; select all relevant releases and preserve versions |
| A13 Consumer recalls | [CPSC API guide](https://www.cpsc.gov/s3fs-public/RecallRetrievalWebServicesProgrammersGuide20180917.pdf) | Public recall web service; verify live query schema before production | Consumer-product scope; industrial safety, medical and automotive products need separate authorities |
| A14 US rules | [Federal Register API](https://www.federalregister.gov/developers/documentation/api/v1) | Structured document search and original-rule links | Rule publication, proposed rules and effective implementation are distinct events |
| A15 Trade screening | [ITA Consolidated Screening List](https://www.trade.gov/consolidated-screening-list), [migration guidance](https://developer.trade.gov/how-to-migrate) | Official downloads or current developer-platform API credentials | US list coverage; not a complete global policy engine or transaction-specific legal determination |
| A16 Minerals | [USGS Mineral Commodity Summaries](https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries) | Download annual reports and available machine-readable data releases; record revisions | Lagged country/material aggregates; distinguish mine production, reserves and processing |
| A17 Storage comparison | [DOE cost/performance assessment](https://www.energy.gov/cmei/2022-grid-energy-storage-technology-cost-and-performance-assessment), [reports/data](https://www.energy.gov/energy-storage-grand-challenge/energy-storage-reports-and-data) | Published reports and linked models/data; store edition and assumptions | Historical technology-level baselines, not live quotations or guaranteed project performance |
| A18 Semiconductor industry | [SEMI Market Intelligence](https://www.semi.org/en/products-services/market-intelligence) | Public summaries plus licensed reports/data products if approved | No public API assumed; purchased reports may restrict extraction and redistribution |
| A19 Patents | [USPTO Open Data Portal](https://data.uspto.gov/) | Validate current portal product/authentication and bulk/API route; reuse existing patent pipeline where equivalent | Jurisdiction/family/assignee coverage must be measured; patenting does not prove commercialization |
| A20 Grid/project data | [EIA Open Data](https://www.eia.gov/opendata/), [EIA generator survey files](https://www.eia.gov/electricity/data/detail-data.php), [CAISO OASIS API](https://www.caiso.com/documents/oasisapispecification.pdf) | EIA registered API key for relevant series; download inventory workbooks; OASIS report requests for selected price products | US pilot only; inventory and market data are separate datasets, with different lags and geography |
| A21 Labor comparator | [BLS API guidance](https://www.bls.gov/developers/api_FAQs.htm) | Time-series requests; choose occupational/industry/geographic datasets and inspect their release availability | Wage series are not a customer's all-in labor expense; include benefits, shifts and utilization assumptions separately |
| A22 Discussion | [Reddit API documentation](https://www.reddit.com/dev/api/) | Existing OAuth credentials; hourly private individual research capture with refreshable storage | Historical reach and deletions limit reproducibility; bots and duplicate posts can distort counts |
| A23 Search interest | [Google Trends API alpha](https://developers.google.com/search/apis/trends) | Apply for access; approved exports if API access unavailable | Restricted availability; normalized interest is not absolute search volume, demand or sales |
| A24 Licensed enrichment | [EODHD API catalog](https://eodhd.com/financial-apis/); provider contracts for consensus, teardowns and commodity assessments | Identify an entitled provider and run a sample export/API proof before selection; API route unresolved for unselected providers | Do not budget paid fields as available until coverage, point-in-time history and usage rights are confirmed |
| A25 Trade flows | [UN Comtrade](https://comtrade.un.org/), [developer portal](https://comtradedeveloper.un.org/) | API/download route; portal/account and quotas depend on access tier; current authentication needs a pilot | Country/product trade, not named company supply chains; preserve reporter, partner, direction, HS edition and quantity units |
| A26 Robotics industry | [IFR World Robotics](https://ifr.org/worldrobotics?id=about-ifr) | Public summaries and licensed detailed statistics/reports; API not assumed | Annual regional/application aggregates and survey scope; assess comparability between industrial and service robotics |
| A27 Trial registries | [ClinicalTrials.gov API v2 introduction](https://www.nlm.nih.gov/pubs/techbull/ma24/ma24_clinicaltrials_api.html); existing EMA CTIS/MHRA/PMDA/ChiCTR/NMPA source registry | Reuse current trial adapters and snapshots; validate version/history retrieval and original protocol/result attachments for each registry | Existing source rows do not prove historical site status, endpoint revisions or operational metrics; regional access gaps remain explicit |
| A28 Regulatory clinical evidence | [Drugs@FDA](https://www.fda.gov/drugs/drug-approvals-and-databases/about-drugsfda), [EMA medicines](https://www.ema.europa.eu/en/medicines), [Health Canada NOC](https://www.canada.ca/en/health-canada/services/drugs-health-products/drug-products/notice-compliance/database.html); official MHRA decisions via existing source registry | Original reviews/labels/decision documents, EMA downloadable medicine tables and Health Canada extracts; extend existing collectors after sample/schema checks | openFDA records do not equal complete review packages; EMA centrally evaluated medicines are not all national approvals. Private scientific advice is not presumed public |
| A29 Guidelines and payer policies | [NICE syndication](https://www.nice.org.uk/reusing-our-content/nice-syndication-api), [NICE reuse terms](https://www.nice.org.uk/reusing-our-content/nice-uk-open-content-licence), [CMS Medicare Coverage Database](https://www.cms.gov/medicare-coverage-database/); indication-specific society and payer sites | NICE access/license and AI-use review; CMS API/download/archive routes to validate; permitted versioned society/payer HTML/PDF captures | Dedicated collector/history not verified. Scope, geography, copyright and edition availability differ; do not assume universal guideline or payer coverage |
| A30 Clinical literature and methods | [PubMed downloads/E-utilities](https://pubmed.ncbi.nlm.nih.gov/download/), [Europe PMC REST](https://europepmc.org/RestfulWebService); existing Crossref proceedings and original publisher/society sources | Metadata APIs/bulk files; permitted open-access full text and supplements; link DOI/PMID/trial IDs and preserve versions | New clinical full-text adapter needed; Crossref metadata is not complete methods/results or a historical citation graph. Check individual full-text reuse rights |
| A31 KOL financial disclosures | [CMS Open Payments](https://www.cms.gov/priorities/key-initiatives/open-payments), [published datasets](https://openpaymentsdata.cms.gov/datasets); original author/society/institution disclosures | Versioned general/research/ownership payment downloads; validate current API/catalog before implementation and link recipient/sponsor identities | New collection needed; publication lag and corrections matter. US reporting scope is limited and not a global register; lack of matching payments is not lack of conflicts |
| A32 Site compliance evidence | [FDA Data Dashboard](https://www.fda.gov/about-fda/performance-data/fda-data-dashboard), linked inspection/compliance datasets and original enforcement documents | Official exports and document capture; resolve investigator/facility identity and finding/resolution dates | New trial-site mapping needed. Public finalized inspections are incomplete operational histories; distinguish manufacturing facilities from clinical investigator sites |
| A33 Independent grants | [NIH RePORTER API](https://api.reporter.nih.gov/); official grant-award and institutional announcements | Project/publication search, stable project/award/PI IDs, organization and dated award amounts; corroborate on funder pages | New enrichment to verify; award, obligated funding and received cash differ. NIH coverage is not all Western funding |
| A34 Institutions and scientific societies | Verified hospital/university/laboratory/society domains, original trial-center directories, biographies, programs and disclosure pages | Explicit domain/page allowlist per institution, permitted HTML/PDF snapshots and RSS where offered; link to B01/B03 | New specialist extraction needed; no universal API or full historic staffing/capability archive assumed. Marketing claims need corroboration |
| A35 Optional private clinical/operational enrichment | Sponsor/CRO/site aggregate exports; licensed utilization, cost and external-control datasets from a provider selected only after access review | Data-use agreement, schema/field/sample verification and secure export route before selection; avoid patient-level inputs for the public-data pilot | No existing access asserted and no provider selected. Site metrics, claims and individual-patient cohorts may be unavailable by January 15; no fabricated substitutes |
| A36 DataForSEO | [Historical Keyword Data](https://docs.dataforseo.com/v3/dataforseo_labs-google-historical_keyword_data-live/), [Trends](https://docs.dataforseo.com/v3/dataforseo_trends-overview/), [organic SERP](https://docs.dataforseo.com/v3/serp/google/organic/live/advanced/), [historical SERPs](https://dataforseo.com/help-center/historical-serps), [authentication](https://docs.dataforseo.com/v3/auth/) | Existing account reported by user; validate API login/password, selected endpoints, returned history, usage rights and task costs in a bounded pilot; reuse shared storage/checkpoint conventions | Account availability is not verified dataset coverage. Keep keyword volumes, trend indexes and search ranks distinct; location/language/history support varies. No authenticated requests performed for this planning update |

## Regional expansion

For biotech, retain the explicitly scoped Western-validation jurisdictions separately from global trial coverage. Begin with sources already represented in the company universe, then measure missing jurisdictions explicitly. Proposed additional discovery sites include [CNINFO](https://www.cninfo.com.cn/) for mainland-China disclosures and [EDINET](https://disclosure2.edinet-fsa.go.jp/) for Japanese filings. Update 2026-10-11: EDINET API credentials are configured in Secrets Manager; recent (2026-10-09) and historical (2021-01-04) filing lists and one PDF from each date were successfully retrieved. See [access verification](data-collection-processing/reports/edinet-access-check.json). EDINET daily capture, historical backfill, issuer mapping, language extraction, reuse review and Athena publication remain outstanding; sample access is not complete collection. CNINFO integration remains separate and unimplemented. Add Korean and other local filing/market sources through the same acceptance process rather than claiming global coverage from US/Hong Kong data.

For procurement, mineral controls, electricity markets and permits, record a source registry per jurisdiction. Capture original-language documents and translation versions. Company headquarters, supplier ownership, facility location, customer location and sales-market exposure must be separate geographic fields.

## Implementation approach

### Reuse before adding collectors

The existing repository contains `sec_filings.py`, `disclosure_collection.py`, `market_collection.py`, `market_operations.py`, `eodhd_daily_cohort.py`, `news_collection.py`, `patent_collection.py`, `patent_bigquery_collection.py`, `people_social_collection.py`, `personnel_archive.py` and `collection_storage.py`. Their presence is a reuse opportunity, not proof that the required specialist fields are covered. Inspect S3 manifests, failed windows, entity coverage and access contracts before assigning a dataset “ready” status.

Do not revive archived IBKR collection. Keep existing quota controls and shared memory/locking behavior. The current market-coverage and NMPA alerts are coverage evidence, not evidence that every source in this plan is healthy. This planning work does not fix or suppress those source failures.

### Source-to-event processing

1. Create an allowlisted source registry: provider, jurisdiction, dataset, access method, credential reference, license, rate budget, pagination, expected cadence, historical bounds and owner. Never put credential values in Markdown or raw evidence.
2. Save raw responses/documents to existing immutable S3 evidence paths, with URL, native ID, HTTP result, retrieval timestamp, checksum and collector version. Reuse collection manifests and checkpoints for resumability.
3. Normalize into company, security, product, indication, trial, site, institution, project, person, contract, benchmark, measurement and event tables. Preserve original values/units beside normalized fields.
4. Extract candidate events with quotations or table/page coordinates and source IDs. Model extraction may propose fields, but unsupported quantities remain null and uncertain event/entity links remain review candidates.
5. Merge sources describing the same action using entity/product/site/time/stage keys. Preserve conflicting claims, revisions, cancellations and source dependence instead of averaging them away.
6. Publish verified datasets through the existing S3/Athena process. Build each specialist's current assessment, change, confidence/coverage and next milestone from dated evidence.

### Minimal record contract

| Record group | Required fields |
|---|---|
| Identity | `company_id`, legal entity/source identifier, optional `listing_id`, `product_id`, `indication_id`, `trial_id`, `site_id`, `institution_id`, `person_id`, `project_id`; counterparties and their roles |
| Timing | `event_at`, `published_at`, `first_observed_at`, `retrieved_at`, `valid_from`, `valid_to`, date precision/timezone and availability basis |
| Evidence | `source_id`, native record ID, canonical URL, raw S3 key, content hash, document version, extractor version, quoted evidence/table/page location |
| Event | Event type, stage, status, previous event/revision ID, quantities/units, currency/base year, conditions precedent and cancellation/expiry |
| Measurement | Application, product/hardware/software version, protocol, comparator, environment, sample/exposure denominator, value/range, original and normalized units |
| Quality | Vendor/independent/official classification, directly observed/claimed/derived/proxy label, coverage gaps, extraction confidence, reviewer and reason |

A source's original publication date is not automatically our first availability date. Preserve the difference between reconstructed historical public evidence and records actually observed at the time. Unknown dates stay unknown; later corrections must not silently rewrite historical model inputs.

### Missing and unreadable data

The user's current PDF policy is to skip pages with no extractable text without sending an alert. Retain original PDF evidence and skipped page numbers; set extraction completeness accordingly, including when the entire PDF is textless. A skipped document is not proof that no deployment, risk or event exists. This policy does not authorize skipping HTTP errors, invalid schemas or incomplete pagination as if collection succeeded.

For private metrics, record `unavailable_publicly` separately from `not_collected`, `source_error`, `not_applicable` and `not_disclosed`. Confidence should fall when necessary evidence is missing; company quality should not be automatically scored lower.

### Scheduling, storage and backfill

- Store all source and prepared data durably in S3. Training/test preparation uses direct S3 reads or Athena in at most one consolidated daily run, as specified above; source ingestion and monitoring have separate cadences.
- Match polling to source release speed: daily for material events, weekly for technical catalogs, monthly/annual for official releases. Conditional requests/content hashes reduce unchanged downloads. Operational checkups remain every 30 minutes.
- Start historical discovery at 2021 where supported, with declared source-specific start dates, security listing dates and gaps. Jobs and website changes usually require prospective capture; do not promise a reconstructed complete archive.
- Respect provider budgets; backfill in resumable windows and prioritize currently tracked companies, products and customers. Retry transient errors with backoff; retain unknown/partial windows instead of marking them complete.
- The 30-day retention rule applies to monitoring alerts/checks. Do not apply it to source evidence or specialist history; those require the research retention policy and any provider-specific restrictions.
- Maintain the consolidated 12-hour error digest; source failures remain inspectable between emails. Changes to access costs or licensed datasets require a separate implementation decision.

## Acceptance criteria for each dataset

A dataset is ready only after its source owner and implementation have demonstrated:

- Permitted access, any credentials/entitlement, budget and a working sample retrieval.
- Explicit geography/entity/date scope, field mapping and historical limits.
- Stable IDs, pagination/count reconciliation and no duplicate records on replay.
- Correct units, currency, timezones, stage distinctions and company/product joins.
- Saved raw evidence and reproducible extraction with reported skipped/unknown fields.
- A recent incremental run, a historical-window replay and a controlled failure/retry test.
- A coverage report showing completed, empty-verified, partial, failed and unavailable windows separately.

Suggested first pilot: choose three tracked companies per sector, cover their latest reporting period and one older quarter, and build C01/C03/C11 plus one sector-specific dataset. Compare extracted events to original evidence before expanding coverage. In parallel, verify biotech B01–B07 and model datasets C13–C15 against the October 5–January 15 calendar; add C05/C07 and storage E02–E04 as scheduled. Defer paid enrichments until their incremental value and access are established.

## Finlight upgrade — October 11, 2026

Pro upgrade reported; January 2021 article access verified with the existing key. The separate bounded backfill covers January 1, 2021 through October 10, 2026 for the four configured English/Chinese sector searches. Existing news timers are enabled; first scheduled historical commit remains to be verified. An email downgrade notice is configured to wait for complete scoped collection, matching Athena verification receipts and current daily capture. The user will then return the subscription to Pro Light manually. See [scope, budget and completion conditions](data-collection-processing/FINLIGHT_BACKFILL.md).

## EIA API access — October 11, 2026

The `EIA` Secrets Manager credential is configured and verified. US all-sector monthly retail-price samples returned for January 2021 and July 2026 (latest returned). Existing EIA860M workbook collection is separate and does not require this key. Required API-series selection, scheduled capture, complete history and Athena publication remain outstanding. See [access evidence](data-collection-processing/reports/eia-access-check.json). No further EIA registration action is needed.

## SEMI cost decision — October 11, 2026

S60 is optional and deferred: the user reports an approximately USD 2,000 report price and no API for the evaluated offering. No purchase is required for the current scope. Evaluate issuer filings and earnings materials, fab/project announcements, government disclosures and public industry summaries for the specific required fields. Preserve publication dates, units, geography and capacity-versus-utilization distinctions. Missing licensed historical detail remains a documented gap; public substitutes are not assumed equivalent.

## S62 and S63 cost decisions — October 11, 2026

Paid teardowns, grade-specific material-price feeds (S62), and Reddit commercial/API/history access (S63) are optional and deferred at the user’s request due to cost. No purchase or paid-access application is required for the current scope. This supersedes earlier Reddit acquisition priorities. Keep missing licensed measurements explicit; public technical/economic data must not be labeled as equivalent teardown or grade-specific prices. Use public substitutes only for their own measurements. Paid Reddit archives remain deferred; bounded Reddit API collection is now live as described below.

## Reddit production collection — October 11, 2026

Existing credentials now support hourly production capture for private, individual research. The first run saved 639 posts and 12 comments and verified all 651 records in `optima_social_research.reddit_records` (workgroup `optima-social-research`). `optima-reddit-collection.timer` runs around minute 15 hourly, with up to two minutes jitter; it replaces the credential-only timer.

Recent searches and selected comment threads are sampled across four sectors. Older ranked searches resume from saved cursors, excluding pre-2021 records; neither search exhaustion nor current engagement on older posts certifies a complete historical archive. Storage is refreshable, capped at 5,000 records / 16 MiB. Each run revalidates records older than 12 hours and discards content unverified for 24 hours; downtime delays cleanup. Issuer linkage remains unresolved. No user credential/approval task remains; paid archive acquisition is deferred. See `data-collection-processing/reports/reddit-collection-latest.json`.

## Social schedules and Google Trends application — October 11, 2026

Google Trends: user has applied for API access. Await approval and credentials; do not repeat the application or mark capture started.

Reddit: hourly content capture replaces the earlier credential-only check; see the production collection section above.

Bluesky: existing optima-social-daily.timer enabled at 06:45 UTC (up to two minutes jitter). Four sector searches, at most ten pages per sector per run, resumable closed daily windows from existing checkpoints. October 11 public endpoint retry still returned HTTP 403. The schedule remains an access/capture attempt, not verified data availability; historical coverage remains incomplete.

## FDA credential configured — October 11, 2026

The FDA secret (JSON field `key`) is now resolved by the shared EvidenceClient for HTTPS api.fda.gov requests. Existing regulatory and specialist FDA daily/historical jobs use it on their next invocation; no new timer is needed. Credentials use an Authorization header and redirects are disabled for authenticated default transport. Three one-record authenticated probes passed: applications, January 2021 submissions and public CRLs. These verify sample access, not completed backfill or original review PDFs. [Evidence](data-collection-processing/reports/fda-access-check.json).

## S35 FDA Data Dashboard access verified — October 11, 2026

Configured FDA-Data secret separately from openFDA. Five one-record probes passed: latest inspection classifications, inspection citations, compliance actions, import refusals, and January 2021 inspections. All returned HTTP 200 and DDAPI application status 400 (documented success). Sample access does not establish complete history. A compliance sample has ActionTakenDate 2026-10-29, later than the probe date; flag future dates during ingestion rather than treating them as confirmed past events.

Remaining work: implement resumable bounded capture and reconciliation, issuer/FEI mapping, Athena publication/coverage checks, and original 483/warning-letter document retrieval. Daily capture and backfill have not started. No further credential request is needed for these tested endpoints. [Access evidence](data-collection-processing/reports/fda-dashboard-access-check.json).

## FDA Product Code Builder — October 11, 2026

FDA-ProductCodes secret configured separately in config/fda-productcodes-access.json. Official blood/plasma product-name lookup verified: HTTP 200, APIRETURNCODE 400, success message, two results with five columns. This removes the credential blocker for optional product-code enrichment of FDA/import records. Full reference extraction, dataset joins and recurring refresh are not yet implemented; no historical coverage claim. [Verification evidence](data-collection-processing/reports/fda-productcodes-access-check.json).

## FDA Enforcement Reports access verified — October 11, 2026

FDA-Enforcement secret configured separately in config/fda-enforcement-access.json. One bounded iRES recall request with January 2021 event modification-date filters returned HTTP 200, application status 400 with success, and one result row (RESULTCOUNT 291). This verifies sample recall access only; modification dates are not recall initiation dates and do not establish a point-in-time archive. No daily capture/backfill or Athena publication was started. Remaining work: collector/pagination integration, date verification, issuer mapping, openFDA overlap reconciliation and publication. [Verification evidence](data-collection-processing/reports/fda-enforcement-access-check.json).

## October 11 schedule deployment — supersedes earlier “integration pending” notes

FDA Dashboard, iRES recalls, EDINET filing metadata and EIA US all-sector monthly retail prices now have bounded daily and historical adapters and enabled systemd timers. Current FDA industry-code reference refresh is daily only. The authenticated lane has a separate lock and 192 MiB per-service cap, 12 scopes/two pages per scope per invocation, daily 07:10 Europe/Madrid plus hourly continuation and hourly historical runs near minute 50. Completed scopes queue for the existing shared specialist Athena publisher; raw capture is not publication. Historical EDINET inventory does not yet download every original document; FDA original 483/review/warning-letter extraction remains separate.

Live first daily commits include EDINET metadata, FDA citation/import/refusal/recall pages, compliance records and the 89-row industry reference. SAM.gov remains HTTP 404, Bluesky HTTP 403, Reddit hourly content capture active with partial historical search coverage, and Google Trends approval pending. Finlight archive collection reached exclusive cursor 2021-01-05; verification/downgrade notice is not yet complete. [Live schedule audit](data-collection-processing/reports/collection-schedule-audit-2026-10-11.json). [Reconciled source checklist](data-collection-processing/reports/weekly-readiness-2026-10-09/data-sources-and-checks.md).

## Committed data accessible in Athena — October 11, 2026

Verified 11,274,035 saved observations across 58 sources through `optima_collected_data.observations` (workgroup `optima-collected-data`, us-east-1). This includes current FDA, EDINET, EIA, Finlight and NMPA batches, even when their collection windows remain partial. Hourly refresh around minute 35 checks Athena row counts and JSON source/dataset consistency. Source documents remain in S3 with their references in record payloads. Reddit remains in `optima_social_research.reddit_records`. Source-specific curated tables continue separately; historical completeness and issuer mapping are not implied. See [verification evidence](data-collection-processing/reports/committed-athena-latest.json).
