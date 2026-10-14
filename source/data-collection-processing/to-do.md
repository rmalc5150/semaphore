**October 11 deployment:** FDA Dashboard/iRES, EDINET metadata and EIA retail-price daily/historical capture enabled; FDA industry codes current refresh enabled. Follow the reconciled source checklist for remaining work and deferred purchases. Full archives and Athena publication are not yet certified.

**October 11 scheduling update:** Google Trends API application submitted; await approval. Reddit content collection is live hourly around minute 15; first 651 records verified in `optima_social_research.reddit_records`. No user access task. Historical searches are partial samples. Bluesky daily retry 06:45 UTC; HTTP 403 still blocks capture. Times include up to two minutes jitter.

# Remaining work

**Scope update October 11:** S62 paid teardown/material-price feeds and S63 Reddit access are optional and deferred for cost. Earlier Reddit purchase/access tasks below are deferred, not active requirements. Omit dependent features and retain explicit data gaps.

## Finlight temporary Pro upgrade — October 11

- [x] Verify the existing key can retrieve January 2021 articles after the upgrade.
- [x] Enable a separate bounded Finlight backfill and receipt-gated completion email in the existing news workers.
- [ ] Verify the first scheduled historical commit and Athena publication, then complete January 2021–October 10, 2026 for the four English/Chinese sector searches.
- [ ] **Downgrade Finlight to Pro Light after the completion email.** Do not downgrade on a successful sample request or an empty queue alone. [Budget, scope and notification conditions](FINLIGHT_BACKFILL.md).

Updated October 9, 2026. This is the forward work plan; implementation and
verification history belongs in the linked source documents.

## October 9 catch-up results

New capture expansion: [68-source API/capture checklist](reports/specialist-expansion-2026-10-09/source-checklist.csv),
[all 20 layer field requirements](reports/specialist-expansion-2026-10-09/layer-requirements.csv) and
[setup/evidence/gaps](reports/specialist-expansion-2026-10-09/capture-and-review.md).

- [x] Implement additional bounded public-source adapters, validated immutable raw evidence, resumable pagination and isolated publication queue.
- [x] Enable daily specialist checks, hourly 2021 historical archive capture and daily fixed-scope search; retain existing shared lock, source workers and spending limits.
- [x] Validate live historical/current provider pages and archive accepted scoped records to S3 with hash readback; record failed probes and corrections explicitly.
- [x] Map all 20 layers to fields, source IDs and private/licensed/identity/availability gaps; add ROR institution identity as S68.
- [ ] Finish the historical window and linked-document queues; verify managed cycles and each new Athena publication receipt.
- [ ] Resolve zero accepted products and 388 pending company identities; establish dated trial/device/chip/project/site/person joins.
- [ ] Obtain required licensed/private inputs and complete specialist field extraction; metadata/discovery pages do not satisfy measurement requirements.

Use the [updated 67-source list and checks](reports/weekly-readiness-2026-10-09/data-sources-and-checks.md),
[readiness report](reports/weekly-readiness-2026-10-09/readiness-report.md) and
[source acceptance records](reports/weekly-readiness-2026-10-09/source-acceptance-records.json).
Daily tasks below remain open where their full acceptance conditions are unfinished.

- [x] Record the provisional enabled universe (496 companies, 388 pending identities)
  and a versioned pilot of three verified companies per sector; retain collector-epoch differences.
- [x] Execute 18 bounded recent/earlier Q1–Q9 publication checks, 16 field samples
  and two additional nonempty disclosure/personnel samples; preserve query receipts.
- [x] Securely reference the supplied DataForSEO Secrets Manager ARN; complete
  keyword/trend/12-search pilot, raw S3/hash receipts and zero-charge cached replay.
  Actual pilot cost USD 0.03864; 104 of 828 expected keyword-month cells were not returned.
- [x] Capture PubMed/Europe PMC original literature and full-text licenses, original
  FDA review pages, procurement candidates, Intel releases/MLPerf evidence,
  Federal Register documents, EIA battery samples and BLS earnings samples.
- [x] Publish 1,207 sample rows to `optima_source_readiness.source_samples_windows`
  and verify every source/dataset count in Athena; new rows remain excluded from training.
- [x] Record updated patent/news/conference/NMPA progress and preserve market exclusions.
  NMPA now has 7,802 records and next page 395 but is blocked by gateway HTTP 429.
- [x] After explicit user approval, enable bounded weekly search capture Friday
  11:00 Europe/Madrid under the existing shared lock and 256 MiB cap; monthly keyword metrics.
- [x] Give all 67 sources a current decision, evidence and source-specific October 12–16 task.
- [ ] Verify two actual automatic cycles and their publication receipts; full entity/jurisdiction
  denominators, 2021-present history and required-field coverage remain incomplete.
- [ ] Complete shared literature/procurement/technical adapters and original-source allowlists;
  resolve NMPA rate limiting and active per-source entitlements/history gaps; Reddit acquisition is deferred.

## This week — October 5–10, 2026

Use the [daily source-readiness to-do list](../specialist_data_collection_plan.md#daily-to-do-list--october-510-2026) and [source-by-source checklist](../specialist_data_sources_checklist.md). Work **Monday, Tuesday, Thursday, Friday and Saturday**; **Wednesday October 7 is off**. Automated collection continues throughout.

- [ ] **Monday Oct 5:** freeze source/entity scope; check existing Athena routes, repaired collectors and historical gaps.
- [ ] **Tuesday Oct 6:** pilot DataForSEO; establish accepted capture/history routes and original-source allowlists.
- [ ] **Thursday Oct 8:** pilot literature capture; verify trial/regulatory fields and clinical/scientific access gaps.
- [ ] **Friday Oct 9:** pilot priority procurement and technical/energy sources; assign remaining adapters/access blockers.
- [ ] **Saturday Oct 10:** verify ongoing capture, older windows, source-to-Athena evidence and every checklist row; order October 12–16 work.

The linked daily plan supplies concrete steps, timeboxes and completion evidence. No full-history completion is assumed from a sample or healthy timer.

## October 5 repair update

The HTTP 413 fix completed the blocked September 23 patent day: 80,417 records
verified, cursor advanced to September 24. NMPA's pagination parser is fixed and
production passed page 149. Catch-up and sustained NMPA progress still need the
next scheduled-run checks. Ten documented exchange-holiday exclusions now join
the eight pre-IPO exclusions; other market gaps remain open. See the
[repair evidence and remaining work](reports/collection-repair-2026-10-05.md).
No credential or paid-plan change is required. Use fresh post-repair failure
evidence before submitting the older NMPA support-ticket draft below.

## Earlier tasks — September 28–October 4, 2026

Work on both patent and NMPA reliability, with daily patents first. Target the
repair work by Friday, October 2; use the next scheduled runs and 12-hour digest
to verify recovery. These are to-do targets, not booked calendar appointments
or automatically scheduled coding sessions.

- [ ] **Daily patents: repair repeated HTTP 413 failures — target September 29.**
  Reserve a 60–90 minute repair session with Codex or the developer maintaining
  collection. The September 28 inspection found 66,652 committed records for
  September 23, blocked in hour 20; the source returned HTTP 413 on repeated
  attempts. The existing adaptive recovery handles changing counts but not 413.
  Implementation brief: inspect the exact failed request, add a bounded fallback
  for 413 using smaller requests/pages or query partitions as supported by live
  validation, and preserve completed hours and existing stream progress. Avoid
  changing the global page-size configuration in a way that silently creates a
  new stream or skips records. Test fallback, repeated failure, count drift,
  interruption/resume and evidence preservation before running the repaired
  service through its existing lock, timeout and request budget.
  **Your action:** bring the error summary to the repair session; ask for this
  bounded recovery fix and its completion evidence. No credential change, plan
  upgrade or repeated manual restart is indicated by the inspected logs.
  **Done when:** a complete committed September 23 daily manifest is verified,
  the daily cursor advances to September 24 or later, subsequent catch-up makes
  progress, and a fresh health check/digest confirms the relevant failures have
  recovered. More committed partial records alone are not sufficient.

- [ ] **NMPA: investigate intermittent rendered-page failures — target September 30.**
  Allow 20–30 minutes to open a Decodo support ticket and record its reference.
  The repaired collector progressed beyond page 88, but the September 28 run
  stopped at page 148 after four HTTP 202 responses that did not pass validation;
  2,888 inventory records were committed. Use the following support request:

  > Our NMPA inventory uses the Decodo Web Scraping API with `proxy_pool=premium`,
  > `headless=html`, default geographic routing, and a browser action waiting up
  > to 15 seconds for `table.searchTable`. The target is
  > https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml?keywords=&currentpage=148
  > On September 28, 2026, the run ending around 04:17 UTC stopped after four
  > target HTTP 202 responses without a validated requested listing page. Other
  > requests have returned valid listing rows even with HTTP 202. Please inspect
  > the failed requests and recommend a supported rendering/wait configuration
  > that reliably returns the requested page, registration rows and pagination.

  **Your action:** submit that text through your Decodo account's support channel,
  add the failed request IDs from its dashboard if available, then bring the
  ticket reference and response back to the repair session. If you do not have
  account access, ask the account owner to submit it. No support message has
  been sent on your behalf.
  **Implementation follow-up:** assess the provider's recommendation and bounded
  retry/recovery changes. Continue to require the exact page number, expected
  rows and consistent totals; HTTP 202 alone must never count as success.
  **Done when:** production advances beyond page 148 with verified saved rows,
  continues across successive scheduled attempts, and the fresh health report
  shows recovery or a specific remaining provider limitation. Full inventory
  coverage remains a separate requirement; one successful page is insufficient.

- [ ] **Review recovery and remaining gaps — target October 2.**
  Read the next 12-hour summary after the repairs and compare it with fresh
  service/checkpoint evidence. Confirm patent dates advance and NMPA pages
  advance; record remaining blockers and the Decodo ticket status here. Leave
  recovered patent backfill on its existing schedule and daily query budget.
  Market exclusions are separate: retain the eight reviewed pre-IPO windows
  and keep unexplained gaps visible until supported by listing/provider evidence.

References: [patent operations](PATENT_OPERATIONS.md),
[regulatory collection](REGULATORY_COLLECTION.md),
[market exclusion review](reports/market-coverage-review-2026-09-27.md).

## Scope and sequence

Cover **biotech, robotics, semiconductors and energy storage**, with **five
specialist layers per sector** (20 total). The sequence is:

1. Verify daily and historical collection for all four sectors.
2. Finalize the five specialist-layer definitions for each sector.
3. Check that every layer's required data is present, correctly stored and usable.
4. Build and validate specialist models while historical backfills continue.
5. Prepare HMM and TFT input files only when the required data and specialist
   models are ready.

**All markets are in scope**; companies are not restricted to HKEX listings.
Sector eligibility and company identity review still apply.

Historical collection starts **January 1, 2021**. Previously published 2015
patent records remain available but do not change the active backfill start.
IBKR is excluded. Preserve source records for later event creation: a press
release, filing and trial update may describe the same event. Collection does
not by itself establish event equivalence or a confirmed personnel movement.

## Current baseline — retain and monitor

Collection and publication paths are implemented for news, market prices and
splits/dividends, patents, SEC/HKEX disclosures, clinical/regulatory sources,
DOI proceedings and initial personnel sources. Initial Athena partitions are
verified; this does **not** establish complete sector or historical coverage.
Personnel feeds and archive scanning are scheduled, with first candidate
partitions verified. Company-profile collection and publication/review paths
need reconciliation against the latest cohorts.

All 15 timers were enabled at the latest restart. Jobs have a shared 2 GB memory
ceiling, heavy-job serialization and per-service limits to support the 4 GB
host. Daily collection and checkpointed historical backfills continue throughout
the phases below, within existing provider quotas and query budgets.

## 1. Verify collection across all four sectors — current priority

- [x] Create a source-by-sector coverage register: required companies and
  geographies, daily freshness, earliest/latest usable dates, missing periods,
  access limits, raw S3 location, curated Athena tables and last verification.
  Distinguish implemented, collected, published and verified status.
  Created: [coverage register](SOURCE_COVERAGE_REGISTER.md), with CSV/JSON and
  linked verification receipts. Unknown usable dates and per-company gaps remain
  explicit; the register is not certification of complete coverage.
- [ ] Reconcile register entries against live committed raw checkpoints and
  company/query/date requirements; verify access, exact missing periods and
  historical usability. Refresh the register as verification progresses.
  First live reconciliation completed September 25: [findings](COVERAGE_RECONCILIATION.md)
  and [query/date gaps](reports/live-coverage/query-date-gaps.csv). Remaining:
  source-specific historical access, listing lifecycle adjudication, snapshot
  history contracts and point-in-time availability. Keep this task open until
  those gaps are resolved; a successful metadata audit is not full readiness.
- [ ] Verify each required source end to end: access, pagination, source totals,
  checkpoints, interrupted-run recovery, revisions, duplicate handling, raw
  read-back, publication and Athena queries. Record unavailable history and
  failed/partial windows explicitly; a working sample is not complete coverage.
  September 25: 257 contract tests passed, 22 source/dataset partition checks
  passed fresh Athena counts, and separate patent/inventory queries succeeded.
  [Verification matrix and blockers](SOURCE_END_TO_END_VERIFICATION.md) keeps
  inaccessible sources and historical-usability gaps open.
- [ ] Expand and review the company universe: legal company versus listing,
  subsidiary and ADR; identifiers and aliases; four-sector memberships;
  outstanding display-company decisions; and private-company discovery.
  Preserve the universe version used by each historical window.
  September 25: universe 0.5 published; four new discovery candidates, five
  registry identity promotions, display decisions resolved, 20 identifier
  checks and 29 alias collisions reviewed/flagged. Still 388 pending identities;
  do not treat this as a complete global universe review.
- [x] Finalize the company admission policy: distinguish first discovery,
  verified sector eligibility and activation of detailed tracking. Record the
  discovery source/reason, first observed time, supporting source dates and
  watchlist activation time. All markets are in scope, confirmed September 25,
  2026; HKEX is one discovery venue, not an eligibility restriction. Apply
  sector and identity checks across markets. Keep historical
  watchlist membership separate from retrospective collection for today’s list.
  Implemented policy 1.0 and 108 dated admissions, published with universe 0.5:
  [admission policy and review](COMPANY_ADMISSION.md).
- [ ] Continue personnel-announcement retrieval from news archives and company
  filings; inspect missed matches and false positives in all four sectors.
  Expand publisher/company coverage and retain source lineage for later events.
  September 25: nine feeds; retrieval 2.1 fixes two inspected misses and flags
  job openings, negated layoffs and uncertain company/sector matches. Historical
  source retrieval and publication continue under the existing memory caps.
- [ ] Prioritize **Reddit** for social collection across the four sectors,
  scoped to the companies explicitly selected for tracking. Maintain a versioned
  watchlist of company IDs, names, aliases, tickers and relevant products;
  distinguish ambiguous ticker/name matches from supported company mentions.
- [ ] Obtain **historical Reddit and company-specific search-ranking data**
  for tracked companies, targeting January 2021 onward plus recurring daily
  collection. These are required datasets; provider access, cost, historical
  depth and sampling frequency still need verification. Record unavailable
  periods explicitly rather than substituting current snapshots. Define the
  search queries, company domains, engines, countries and languages to track;
  keep discovered-page collection distinct from measured ranking history.
- [ ] Version search queries and capture engine/provider, locale,
  language, observation time, result URL/title/snippet, rank and result type.
  Preserve retrieved pages separately with their own provenance; deduplicate
  against news/filings and resolve company matches. Verify S3/Athena publication
  and daily refresh. Current results cannot reconstruct historical rankings,
  and an old page date does not establish past search visibility.
- [ ] Record other social-source gaps without displacing Reddit as the priority.
  Bluesky search currently returns HTTP 403; access and history remain unverified.
- [ ] Close regulatory gaps: NMPA inventory/detail completeness and recurring
  reconciliation, historical versions, and geographic coverage beyond existing
  SEC/HKEX and clinical/regulatory paths.
- [ ] Extend conference/publication coverage beyond DOI proceedings to relevant
  conference websites, presentations and journal-supplement abstracts.
- [ ] Verify company-profile cohorts collected in S3 reach the appropriate
  Athena observation tables and reviewed universe releases. Raw profile
  publication does not automatically approve identities or sector memberships.
- [ ] Reconcile news history from 2021 onward, price/corporate-action gaps and
  older revisions, patent backfill/publication lag and current global coverage,
  and partnership/licensing/M&A source coverage. Track unavailable action types
  and unsupported ownership or identity links.
- [ ] Observe representative full workloads and at least a complete daily cycle
  under the memory limits. Check failures, queue delays, collection freshness,
  quota use and alerts; optimize remaining large publishers if caps block them.

**Exit condition:** Each currently required source has a verified collection
path and an explicit coverage status for each applicable sector. Historical
backfills may still be running; missing or inaccessible coverage is visible.

References: [migration status](COLLECTOR_MIGRATION.md),
[personnel sources](PEOPLE_COLLECTION.md), [company universe](COMPANY_UNIVERSE.md),
[historical collection](HISTORICAL_COLLECTION.md), [RAM budget](RAM_BUDGET.md).

## 2. Finalize five specialist layers for each sector

The user has supplied biotech outlines. Robotics, semiconductor and energy-storage
layer definitions are still to be supplied and worked through; do not assume
that the biotech roles transfer unchanged to these sectors.

| Sector | Five-layer definition status |
|---|---|
| Biotech | Outlines supplied: Comparator Credibility, Western Validation, KOL, Talent Migration, Trial Quality. Detailed specifications remain. |
| Robotics | Five roles and detailed specifications pending. |
| Semiconductors | Five roles and detailed specifications pending. |
| Energy storage | Five roles and detailed specifications pending. |

- [ ] Work through each of the 20 layers: decision question, unit of analysis,
  relevant event types, required source fields, scoring/output meaning,
  uncertainty, missing-data behavior, update rules and validation criteria.
- [ ] Define how source records become linked events and how each event routes
  to one or more relevant layers. Preserve independent source records,
  contradictions and revisions; avoid counting repeated reports as new events.
- [ ] Map every layer requirement to the coverage register. For biotech, resolve
  guidelines and payer policies, independent validation, KOL identities and
  disclosures, company milestone timelines, and trial-site operating history.
  Record equivalent requirements as the other sectors' layers are defined.

**Exit condition:** All 20 layer specifications and their data requirements are
settled, with collection gaps returned to phase 1. Implementation follows phase 3.

## 3. Double-check data readiness against the layer definitions

- [ ] Check every required field against representative source records in each
  sector: meaning, completeness, accuracy, units, timestamps and granularity.
- [ ] Verify immutable originals and manifests are in S3, curated records are
  queryable in the intended Athena tables, and counts/checksums reconcile.
  Confirm specialist consumers can retrieve the agreed schema and versions.
- [ ] Validate stable company, listing, product/program, person, trial/site and
  event identifiers where applicable. Preserve uncertain relationships and
  deduplicate observations without discarding source provenance or revisions.
- [ ] Distinguish event date, publication date, collection time and verified
  availability time. Current snapshots must not masquerade as historical
  versions; exclude unverified availability from point-in-time inputs.
- [ ] Define and validate the event and specialist input/output contracts,
  including missingness, confidence, source references and version metadata.
- [ ] Check Reddit and search-result data for company-match errors,
  reposts, promotional/spam content, source dependence and time-varying metrics.
  Treat discussion and search visibility as observations; corroborate factual
  event claims before routing them as confirmed events to specialist layers.
- [ ] Produce a readiness report per sector and layer with usable date ranges,
  unresolved gaps and collection fixes. Recheck it as backfills arrive.

**Exit condition:** Required data is in the right location and form, with
representative usable inputs for every layer and explicit historical gaps.
Missing independent source material must not be replaced by company claims.

## 4. Build and validate specialist models while history downloads

- [ ] Implement the five agreed specialists per sector against the validated
  event/data contracts, including routing, incremental updates and safe reruns.
- [ ] Build reviewed evaluation cases for each layer, including conflicting
  reports, missing information, repeated announcements and later corrections.
- [ ] Validate scoring and uncertainty, source traceability, historical
  availability and performance on time-separated data where applicable.
- [ ] Version models, inputs and outputs; verify outputs are stored and queryable
  in the agreed location and schema for downstream use.
- [ ] Process newly available historical windows incrementally and reconcile
  specialist coverage as collection completes. Do not call a layer validated
  solely because its code executes or a small demonstration succeeds.

**Exit condition:** All 20 specialists meet their defined validation criteria;
required historical source and specialist-output coverage is reconciled. Any
unavailable data requires an explicit scope decision before downstream use.

## 5. Prepare HMM and TFT input files — gated on data and specialists

Do not begin input-file implementation until the required data and validated
specialist models are ready. January 2021 is the intended start, subject to
verified coverage and historical availability.

- [ ] Set targets, prediction frequency, horizons, company/listing universe and
  required specialist outputs for HMM and TFT.
- [ ] Build reproducible, time-aligned inputs with appropriate price/action
  handling, missing-data rules, availability cutoffs and time-based splits.
- [ ] Verify file schemas, shapes, ordering, entity/date coverage and source/model
  version lineage; test for future-information leakage and duplicate events.
- [ ] Reconcile final files against Athena and specialist outputs and record
  readiness before HMM/TFT training or downstream integration.

Later, outside the immediate collection/specialist plan: HMM/TFT model work,
prediction storage in RDS, frontend integration and end-to-end validation.
