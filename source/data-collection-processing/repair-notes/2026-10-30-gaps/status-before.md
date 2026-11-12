# Data-source status — refreshed 28 October 2026

Updated **28 October 2026** from the supplied checkup, live service logs, worker deployment receipts and bounded source replays. The filename is retained for existing links. All **158 catalog entries** and their SQL links remain below, reordered by attention needed. Catalog counts and Athena previews remain the **October 26 baseline**, unless explicitly superseded here; they have not all been rerun today. No source is certified complete from 2016.

## Collection failure policy

A failed source/window is logged and deferred; independent sources must continue. Failed work remains incomplete and visible for repair. October 28 changes isolate publication discovery and source-group exceptions, increase repeated-failure cooldowns, and prioritize lower-attempt historical jobs. Existing concurrency limits and three-attempt parking prevent one failed job from occupying the pool indefinitely. [Implementation, tests and deployment receipts](data-collection-processing/repair-notes/2026-10-28-isolation/README.md).

## Highest-priority repairs and verification

| Priority | Source / pipeline | Position on October 28 | Next step and completion check | Owner |
|---|---|---|---|---|
| 1 | Regulatory publication / 024 NMPA trials | Fixed date conversion that rejected full ISO timestamps. Both previously failing batches now curate successfully, six records each. Fix installed in local publisher code. | Let the serialized publisher process both windows; verify publication receipts and query matching records in Athena. Curation success alone is not Athena verification. | Engineering |
| 2 | 017 FDA openFDA | Fixed undated submissions and duplicate composite identities. Preserve undated evidence explicitly and distinct variants separately. Worker deployment succeeded; June 2016 replay advanced to its two-page bound. | Continue remaining pages, reconcile failed windows and publish/query the resulting records. The bounded replay remains partial. | Engineering |
| 3 | 036 FDA Enforcement / iRES | Fixed the documented response actually observed: status 412, “No results found”, no result array. January 2016 replay completed with zero records. Contradictory/nonempty errors still fail. | Retry other affected scopes and publish coverage receipts. This endpoint's modification-date window does not establish a historical recall vintage. | Engineering |
| 4 | 042 TED, 050 USGS, 057 BLS; retained 055 EIA / 056 CAISO permission failures | Retained historical failures include S3 AccessDenied; worker policy inspection found missing BLS/USGS enrichment paths. No IAM policy changed today. | Match exact denied keys to current worker calls, add only necessary artifact permissions, then replay each source under the worker role. Check TED cache capacity separately. | Engineering |
| 5 | 147 Zenodo, 145 bioRxiv/medRxiv, 143 DataCite | Repeated HTTP 400/provider errors, duplicate IDs, oversized responses and source changes remain unresolved. | Reproduce one failed scope per source; repair request/pagination/identity logic, split oversized scopes, then verify committed pages and Athena payloads. Record pre-launch periods only with evidence. | Engineering |
| 6 | 050 USGS older mineral reports | 2016–2018 archive probes still returned 404; no replacement URLs deployed. | Find official mineral-specific archive files and validate content/identity before mapping them; preserve unavailable years as explicit gaps. | Engineering |
| 7 | 075 ERA5; 066 FRED; 070 Ember; 071–073 WTO; 098 OpenDART; 118 Census; 125 USDA; 051 Comtrade | Current checkup contains failed requests. Keys already exist; these failures do not by themselves establish invalid credentials. | Replay exact requests with current credentials; separate endpoint/request fixes, temporary 5xx responses and actual account denials. Escalate only demonstrated access problems. | Engineering; owner for confirmed entitlement issues |
| 8 | 008 EDINET, 020 MHRA, EMA / ClinicalTrials / Europe PMC / USAspending | Old-date availability, unavailable designation dates, changing pages, count mismatch and exhausted retries remain in the supplied historical checkup. | Verify provider date limits; preserve unknown dates; replay bounded scopes and compare provider counts to committed unique records. Do not clear errors by declaring incomplete history complete. | Engineering |
| 9 | Daily HKEX / dependent disclosures, news and patents; market coverage | Live monitoring still reports changing snapshots/prerequisites and unresolved price coverage. | Repair/restart from valid snapshots; verify daily commits. For prices, separate ticker mappings and evidence-backed impossible periods from genuine missing data. | Engineering |
| 10 | Daily queue waits and search-capture inspection | Authenticated daily, people and health-audit queue waits remain; search inspection is failing. | Inspect lock ownership, age and job duration; restore fair scheduling and a readable search report. Verify fresh daily progress rather than just enabled timers. | Engineering |

**SMS is resolved for this action list:** you confirmed receipt of a text. The watchdog now acknowledges the old delivery alarm using a dated owner confirmation; a newer alarm transition remains actionable. The refreshed monitoring state excludes SMS. No test text was sent.

**Validation today:** 71 tests passed. Three collector modules were deployed to the historical worker (447 copies) and local daily workspaces (48 copies); the regulatory publisher date fix is installed locally. Live FDA/iRES replays and NMPA curation evidence are in [the October 28 repair notes](data-collection-processing/repair-notes/2026-10-28-checkup/README.md). No new Athena completeness claim is made. Historical work remains enabled; existing owner pauses remain unchanged.

## Your actions first

Store newly issued credentials in the existing Secrets Manager secret **`dataSourceAPIkeys`** and add only the field names/status to [apiKeyRegister.md](apiKeyRegister.md). Do not put secret values in this report. A stored key does not establish working endpoints or historical entitlement.

### Approvals already requested

| Sources | Current position and next step | Official instructions |
|---|---|---|
| 078 UCDP organized violence | Already emailed. Follow up with the API maintainer and describe the project; store the issued access token. | [Provider](https://ucdp.uu.se/apidocs/) |
| 088 NICE technology appraisals | NICE replied: submit the syndication application, provide a qualifying cybersecurity certification/report for NICE review (US applicants generally SOC 2 Type II), agree the licence and obtain the API key. Only final published guidance is available; drafts, company submissions, assessment reports and committee papers are excluded. Public daily/historical capture is paused. | [Provider](https://www.nice.org.uk/reusing-our-content/nice-syndication-api) |
| 099 South Korea KOSIS statistical OpenAPI | Already emailed. Follow up on the OpenAPI application and obtain the authentication key. | [Provider](https://kosis.kr/openapi/) |

### Access follow-up — including existing applications and keys

These entries still need owner follow-up. TikTok and X keys are already obtained and are listed separately below; LinkedIn has already been applied for.

| Sources | Steps | Official instructions |
|---|---|---|
| 131 Meta Ad Library API | Complete Meta developer/identity and Ad Library access steps; obtain the token for the approved Ad Library scope. | [Provider](https://www.facebook.com/ads/library/api/) |
| 132 TikTok Commercial Content API | Keys obtained. October 27 token request succeeded; ad queries returned HTTP 500 twice. Engineering must retry and validate the content endpoint; do not apply for another key. | [Provider](https://developers.tiktok.com/products/commercial-content-api) |
| 133 LinkedIn Ad Library / external API | Application submitted. Await LinkedIn’s response; follow up on that application rather than submitting another. | [Provider](https://www.linkedin.com/blog/engineering/trust-and-safety/enhancing-transparency-with-linkedins-ad-library) |
| 134 X Ads Repository DSA API | Keys obtained. October 27 lookup returned HTTP 402 (credits depleted); Ads Repository returned HTTP 403/code 453. Review the account’s Ads Repository entitlement; do not buy credits assuming they resolve a separate product-access denial. | [Provider](https://help.x.com/en/business-and-advertising/ads-transparency) |
| 142 OpenAlex scholarly graph | Create an OpenAlex account, verify the email, then copy the key from Settings → API key; bulk cursor paging requires it. | [Provider](https://help.openalex.org/api/authentication/) |
| 153 Japan KAKEN funded research | Register the application ID used by KAKEN; describe commercial use to NII as required by their guidance. | [Provider](https://support.nii.ac.jp/en/kaken/api/api_outline) |
| 121 Open Supply Hub production locations | Apply for API access; after approval generate a token in My Account > Settings > API. Confirm commercial terms. | [Provider](https://info.opensupplyhub.org/resources/api-documentation) |

### Commercial access decisions

Request a quote only for the full product you want. Existing public summaries/download routes can continue separately. Ask the provider which years are available back to 2016 and which API product includes them.

| Sources | Your next step | Provider |
|---|---|---|
| 114 ImportYeti shipment and supplier relationships | Request API access; confirm volume, history and allowed storage/ML use. Free website access is not bulk API entitlement. | [Provider](https://docs.importyeti.com/docs/getting-started) |
| 115 ImportGenius international shipments | Request an API-enabled plan and token from the implementation team; specify country and historical scope. | [Provider](https://w3.importgenius.com/features/api-integration) |
| 116 MarineTraffic historical vessel tracks and port calls | Request historical vessel-track and port-call API entitlements, not only a website login. | [Provider](https://servicedocs.marinetraffic.com/tag/Vessel-Historical-Track/) |
| 117 Kpler commodity cargo flows | Ask Kpler for cargo-flow API access and authentication for the contracted product; do not assume a MarineTraffic key covers it. | [Provider](https://developers.kpler.com/) |
| 130 Euromonitor Passport Statistics API (paid candidate) | Ask the account team for Statistics API entitlement and the credentials required by the current portal. | [Provider](https://www.euromonitor.com/solutions/passport/connect/api) |
| 135 Sensor Tower / Pathmatics advertising intelligence (paid candidate) | Request Sensor Tower/Pathmatics advertising API and historical entitlements. Exact credential format is not confirmed from public documentation. | [Provider](https://sensortower.com/) |
| 140 Dealroom startup and funding API (commercial) | Request the Premium API key and confirm use restrictions and historical coverage. | [Provider](https://knowledge.dealroom.co/knowledge/dealroom-api-1) |
| 157 Altmetric scholarly attention (commercial) | Request commercial access appropriate to the endpoints; free academic permission is not a commercial entitlement. | [Provider](https://docs.altmetric.com/details-page-api/licensing/) |
| 083 SEMI worldwide equipment billings | Use public releases; request a licence if detailed historical equipment data are required. Public capture remains separate. | [Provider](https://www.semi.org/en/products-services/market-data) |
| 084 International Federation of Robotics World Robotics | Public summaries are not the full licensed dataset; ask for machine-readable access and permitted use. Public capture remains separate. | [Provider](https://ifr.org/worldrobotics/) |

### Credentials already obtained — no repeat application

The register includes the following obtained provider groups, plus TikTok and X above. EPO credentials and first historical/daily captures are verified; earlier presence and endpoint probes cover the other registered groups. Remaining work belongs to integration/testing unless a test establishes a provider-side access problem.

| Sources | Existing secret field(s) | Remaining work |
|---|---|---|
| 051 UN Comtrade | `UN-primary / UN-Secondary (register spelling); deployed presence check found UN-secondary` | Existing UN Comtrade collector has older data and an enabled historical route; validate that the newly supplied subscription fields are mapped, including case-sensitive secondary-field spelling. |
| 066 FRED / ALFRED series and vintages | `FRED` | October 26 probe succeeded; October 28 checkup now includes historical request failures. Repair the failing scope and verify daily and historical commits; the earlier “not enabled” status is superseded. |
| 070 Ember electricity demand and generation | `Ember` | Validate key, configure the endpoint and collector, then verify committed historical and daily captures. |
| 071 WTO Timeseries API; 072 WTO Quantitative Restrictions API; 073 WTO ePing SPS/TBT notifications | `WTO-primary / WTO-secondary` | Validate key, configure the endpoint and collector, then verify committed historical and daily captures. |
| 075 Copernicus ERA5 / ERA5-Land | `copernicus` | Validate the stored token, accept the requested ERA5/ERA5-Land dataset terms in CDS, then implement and schedule the dataset downloader. |
| 098 South Korea FSS OpenDART | `dart` | October 26 probe succeeded; October 28 checkup now includes historical request failures. Repair the failing scope and verify daily and historical commits; the earlier “not enabled” status is superseded. |
| 118 US Census International Trade API | `US-census` | Earlier probe returned a non-JSON response; fix endpoint/response handling and validate the registered key before scheduling. |
| 125 USDA FAS Production, Supply and Distribution | `usda-fas` | Earlier probe returned HTTP 403. Check endpoint/header configuration and the FAS product entitlement; contact FAS only if a correctly authenticated retry is still denied. |
| 074 EPO OPS patent legal events | `EPO-consumer / EPO-consumer-secret` | Historical collection is active on m7i.large; daily discovery and tracked-patent refresh are active on t3. Continue backfill and verify analytical publication; no further owner key application is needed. |

### Existing owner pauses

Marketaux (012), GitHub SDK (044), Reddit (059) and Bluesky (061) remain paused. Their retained data remains queryable where previously published. Resume instructions from you are needed to change those pauses; obtaining a replacement key is not the default fix.

## Earlier operational baseline — unresolved items retained

Historical collection remains enabled on **m7i.large**, with **15 configured workers** sharing **2 CPUs / 6 GiB RAM** (host: 2 vCPUs / 8 GiB). Daily capture/control stay on t3; the latest resize verification recorded 36 active daily timers. Five raw workers, six legacy executors and four public-download workers are configured. Queue jobs marked succeeded can represent one bounded invocation, not a finished source.

October 26 baseline (not recounted October 28): public routes: **73/73 daily attempts**, **73/73 historical attempts**; **61** sources with an artifact and **34** with a non-HTML file. Fresh structured Athena previews returned rows for **69 catalog entries**. Artifact counts are saved objects, not parsed analytical rows or full history.

The following October 26 observations remain a backlog reference unless superseded by the October 28 priorities above. They are not a new live audit of every public route.

| Sources | Observed issue | Fix |
|---|---|---|
| 001 GLEIF legal entities | public_http_404, public_redirect_limit, unreviewed_public_redirect | Replace stale URLs with the current official archive/resource links; retry. Check the provider response, redirect and Decodo/transport logs; repair the route and retry without raising provider limits. Review the official destination and add only approved redirect hosts; retry the affected URLs. |
| 004 HKEX prices | unreviewed_public_redirect | Review the official destination and add only approved redirect hosts; retry the affected URLs. |
| 023 Chinese Clinical Trial Registry | public_http_405 | Correct endpoint/method or use the reviewed Decodo retrieval route. |
| 024 NMPA trials | public_http_202 | Handle the provider challenge/async response and validate returned content. |
| 027 Europe PMC full text | scrape_incomplete_response, scrape_target_http_404 | Validate Decodo rendering/response handling and retry with a bounded backoff. Check the provider response, redirect and Decodo/transport logs; repair the route and retry without raising provider limits. |
| 045 NIST robotics methods | public_http_405 | Correct endpoint/method or use the reviewed Decodo retrieval route. |
| 049 Trade screening lists | ChunkedEncodingError | Check the provider response, redirect and Decodo/transport logs; repair the route and retry without raising provider limits. |
| 052 Department of Energy storage program | public_http_404 | Replace stale URLs with the current official archive/resource links; retry. |
| 082 SIA / WSTS public semiconductor sales | unreviewed_public_redirect | Review the official destination and add only approved redirect hosts; retry the affected URLs. |
| 083 SEMI worldwide equipment billings | scrape_incomplete_response | Validate Decodo rendering/response handling and retry with a bounded backoff. |
| 089 Canada CDA-AMC / CADTH reimbursement reviews | scrape_gateway_http_502, scrape_incomplete_response | Check the provider response, redirect and Decodo/transport logs; repair the route and retry without raising provider limits. Validate Decodo rendering/response handling and retry with a bounded backoff. |
| 090 France Assurance Maladie Open Medic | public_http_410, unreviewed_public_redirect | Find the replacement official resource; record unavailable historical material. Review the official destination and add only approved redirect hosts; retry the affected URLs. |
| 092 CNINFO mainland-China company disclosures | unreviewed_public_redirect | Review the official destination and add only approved redirect hosts; retry the affected URLs. |
| 093 China NBS industrial production | public_http_404 | Replace stale URLs with the current official archive/resource links; retry. |
| 094 China MIIT electronics and battery statistics | scrape_gateway_http_400 | Check the provider response, redirect and Decodo/transport logs; repair the route and retry without raising provider limits. |
| 096 China NHSA reimbursement and procurement | ConnectTimeout, scrape_gateway_http_400 | Check the provider response, redirect and Decodo/transport logs; repair the route and retry without raising provider limits. |
| 101 Taiwan customs trade statistics | scrape_gateway_http_400 | Check the provider response, redirect and Decodo/transport logs; repair the route and retry without raising provider limits. |
| 102 India IBM mineral production | unreviewed_public_redirect | Review the official destination and add only approved redirect hosts; retry the affected URLs. |
| 103 Indonesia ESDM and Geological Agency mineral statistics | public_asset_too_large | Use a bounded streaming download for the large file, then verify checksum and commit it. |
| 104 Brazil ANM mineral yearbook | public_http_404 | Replace stale URLs with the current official archive/resource links; retry. |
| 105 Brazil ANM CFEM mining royalties | public_http_404 | Replace stale URLs with the current official archive/resource links; retry. |
| 106 Brazil MDIC Comex Stat API | public_http_401 | Check whether this endpoint requires authentication or use the documented public export; a missing key is not established by this response alone. |
| 107 Chile COCHILCO production and mining economics | unreviewed_public_redirect | Review the official destination and add only approved redirect hosts; retry the affected URLs. |
| 108 Chile SERNAGEOMIN mining yearbooks | scrape_target_http_404 | Check the provider response, redirect and Decodo/transport logs; repair the route and retry without raising provider limits. |
| 110 Peru MINEM mining bulletins and yearbooks | unreviewed_public_redirect | Review the official destination and add only approved redirect hosts; retry the affected URLs. |
| 113 Peru INGEMMET GEOCATMIN | scrape_gateway_http_400 | Check the provider response, redirect and Decodo/transport logs; repair the route and retry without raising provider limits. |
| 119 Eurostat Comext goods trade | unreviewed_public_redirect | Review the official destination and add only approved redirect hosts; retry the affected URLs. |
| 122 OpenStreetMap / Overpass industrial facilities | ReadTimeout, public_http_502 | Check the provider response, redirect and Decodo/transport logs; repair the route and retry without raising provider limits. |
| 124 European Environment Agency industrial facilities | public_http_410 | Find the replacement official resource; record unavailable historical material. |
| 128 IEA Global EV Data Explorer and Outlook | public_rendered_page_too_large | Check the provider response, redirect and Decodo/transport logs; repair the route and retry without raising provider limits. |
| 148 Semantic Scholar citation context | public_http_429 | Check the provider response, redirect and Decodo/transport logs; repair the route and retry without raising provider limits. |
| 149 France theses.fr doctoral theses | ConnectTimeout | Check the provider response, redirect and Decodo/transport logs; repair the route and retry without raising provider limits. |
| 150 Brazil CAPES theses and dissertations | public_asset_too_large, scrape_gateway_http_400 | Use a bounded streaming download for the large file, then verify checksum and commit it. Check the provider response, redirect and Decodo/transport logs; repair the route and retry without raising provider limits. |
| 154 Brazil FAPESP PIPE and grants | scrape_incomplete_response | Validate Decodo rendering/response handling and retry with a bounded backoff. |
| 155 UKRI Gateway to Research | public_http_400 | Check the provider response, redirect and Decodo/transport logs; repair the route and retry without raising provider limits. |
| 158 University technology-transfer catalogs and reports | public_http_404 | Replace stale URLs with the current official archive/resource links; retry. |
| 042 Tenders Electronic Daily procurement notices (historical structured tasks) | [Errno 28] No space left on device: '/home/ec2-user/data-collection-processing/ted-package-cache/202200085.lock' (4), An error occurred (AccessDenied) when calling the GetObject operation: User: arn:aws:sts::059416028963:assumed-role/constellation-backfill-worker/i-06241bd1c4e91c2fc is not authorized to perform: s3:G (12), [Errno 28] No space left on device: '/home/ec2-user/data-collection-processing/ted-package-cache/202200065.lock' (3), [Errno 28] No space left on device: '/home/ec2-user/data-collection-processing/ted-package-cache/202200107.lock' (1) | Inspect failed-task manifests and correct source parameters/pagination, then retry; keep partial committed pages. |
| 057 BLS wages (historical structured tasks) | An error occurred (AccessDenied) when calling the GetObject operation: User: arn:aws:sts::059416028963:assumed-role/constellation-backfill-worker/i-06241bd1c4e91c2fc is not authorized to perform: s3:G (6) | Inspect failed-task manifests and correct source parameters/pagination, then retry; keep partial committed pages. |
| 050 USGS minerals (historical structured tasks) | An error occurred (AccessDenied) when calling the PutObject operation: User: arn:aws:sts::059416028963:assumed-role/constellation-backfill-worker/i-06241bd1c4e91c2fc is not authorized to perform: s3:P (12), An error occurred (AccessDenied) when calling the GetObject operation: User: arn:aws:sts::059416028963:assumed-role/constellation-backfill-worker/i-06241bd1c4e91c2fc is not authorized to perform: s3:G (4), source_http_404 (16) | Inspect failed-task manifests and correct source parameters/pagination, then retry; keep partial committed pages. |
| 056 California ISO prices (historical structured tasks) | An error occurred (AccessDenied) when calling the GetObject operation: User: arn:aws:sts::059416028963:assumed-role/constellation-backfill-worker/i-06241bd1c4e91c2fc is not authorized to perform: s3:G (56) | Inspect failed-task manifests and correct source parameters/pagination, then retry; keep partial committed pages. |
| 035 FDA Dashboard inspection classifications (historical structured tasks) | source_http_502 (1) | Inspect failed-task manifests and correct source parameters/pagination, then retry; keep partial committed pages. |
| 036 FDA Enforcement Report recalls (historical structured tasks) | Earlier baseline: fda_result_shape (30) | October 28: parser repaired and one empty January 2016 scope completed. Remaining affected scopes and publication still need verification. |
| 008 Japan EDINET corporate filings (historical structured tasks) | edinet_api_status (272), source_http_302 (1) | Inspect failed-task manifests and correct source parameters/pagination, then retry; keep partial committed pages. |
| 055 EIA retail prices (historical structured tasks) | An error occurred (AccessDenied) when calling the PutObject operation: User: arn:aws:sts::059416028963:assumed-role/constellation-backfill-worker/i-06241bd1c4e91c2fc is not authorized to perform: s3:P (16) | Inspect failed-task manifests and correct source parameters/pagination, then retry; keep partial committed pages. |
| 143 DataCite dissertations, datasets, software and usage (historical structured tasks) | additional_response_too_large_split_scope (1), additional_request_failed (2), source_http_503 (1) | Inspect failed-task manifests and correct source parameters/pagination, then retry; keep partial committed pages. |
| 145 bioRxiv / medRxiv preprints (historical structured tasks) | biorxiv_provider_error (41), additional_duplicate_provider_ids (3) | Inspect failed-task manifests and correct source parameters/pagination, then retry; keep partial committed pages. |
| 147 Zenodo research artifacts and usage (historical structured tasks) | source_http_400 (88), source_http_500 (1) | Inspect failed-task manifests and correct source parameters/pagination, then retry; keep partial committed pages. |
| 143 DataCite dissertations, datasets, software and usage (daily structured tasks) | source_changed_refresh_required (5) | Refresh the unstable source snapshot/cursor according to the provider contract, then retry; preserve already committed pages. |
| 147 Zenodo research artifacts and usage (daily structured tasks) | source_changed_refresh_required (8), source_http_500 (1) | Refresh the unstable source snapshot/cursor according to the provider contract, then retry; preserve already committed pages. |

Raw USGS/NSF/arXiv output still needs analytical publication. The five new public structured APIs have visible Athena samples; full publication membership for their newest batches remains unaudited. Discovery-only public routes require resource-specific downloads and parsing; the artifact inventory below exposes file metadata only. Temporary historical gates remain for MLPerf/GitHub shared quota, USPTO assignments and SAM shared budgets. Optional NCBI/BLS keys can improve limits but do not block their public collection. WSTS public history and the selected IEA EV public route do not require buying an API key.

## All 158 sources — attention order, with dated baseline evidence

Daily and historical scheduler counts refer to bounded tasks. Committed observations can include repeated versions and overlapping queries. Requested `[start, end)` windows describe the query envelope, not uninterrupted event-date coverage. An empty completed query is not automatically a gap. Rows with only earlier native audit evidence are labelled accordingly; a configured timer or route is not proof of a fresh successful capture.

**Athena (October 26 baseline):** one-row previews show whether rows are visible now, not full publication completeness. Public artifact SQL returns metadata/URIs, not the contents of binary files. Earlier native row totals are retained for continuity; they are not refreshed totals.

| # | Source | Daily / historical execution | Collected evidence and 2016 scope | Athena / SQL | Next action |
|---:|---|---|---|---|---|
| 024 | NMPA trials (`nmpa_trials`) | Daily: public: 0 files; 1 pages; 2 pending; 2 errors; historical: public: 0 files; 1 pages; 2 pending; 2 errors; 72 succeeded | Earlier native audit: 65,197 committed row occurrences; windows [2021-01-01, 2026-10-16); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 2 artifact metadata rows visible — [SQL](#q024) | October 28: timestamp curation fixed; both failed six-record batches pass locally. Await publisher receipts and Athena queries. |
| 017 | FDA openFDA (`fda_openfda`) | Daily: existing daily schedule; fresh success not audited; historical: 116 succeeded/1 pending | Earlier native audit: 9,446 committed row occurrences; windows [2016-01-01, 2026-10-20) | YES — fresh preview returned rows — [SQL](#q017) | October 28: missing-date/duplicate handling deployed; June 2016 replay partial at page limit. Continue and verify publication. |
| 036 | FDA Enforcement Report recalls (`fda_ires_recalls`) | Daily: existing daily schedule; fresh success not audited; historical: 131 succeeded; structured: 100 complete; 1 partial; 30 failed; 135,036 captured observations | Earlier native audit: 31,304 committed row occurrences; windows [2021-01-01, 2026-10-25); 2016-era coverage not established Current structured scheduler: 100 complete; 1 partial; 30 failed; 135,036 captured observations. Record-bearing requested task envelope [2018-03-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q036) | October 28: empty-response parser deployed; one January 2016 scope complete with zero rows. Reconcile remaining scopes and coverage publication. |
| 042 | Tenders Electronic Daily procurement notices (`ted_notices`) | Daily: existing daily schedule; fresh success not audited; historical: 26 succeeded/1 running; structured: 225 complete; 63 partial; 20 failed; 50,399 captured observations | Earlier native audit: 26,907 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 225 complete; 63 partial; 20 failed; 50,399 captured observations. Record-bearing requested task envelope [2017-01-01, 2022-10-01); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q042) | Technical structured-task failures listed above; repair/retry while retaining committed pages. |
| 050 | USGS minerals (`usgs_minerals`) | Daily: existing daily schedule; fresh success not audited; historical: 107 succeeded; structured: 36 complete; 0 partial; 32 failed; 60 captured observations | Earlier native audit: 176 committed row occurrences; windows [2021-01-01, 2026-10-23); 2016-era coverage not established Current structured scheduler: 36 complete; 0 partial; 32 failed; 60 captured observations. Record-bearing requested task envelope [2021-01-01, 2026-10-10); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q050) | Technical structured-task failures listed above; repair/retry while retaining committed pages. |
| 057 | BLS wages (`bls_wages`) | Daily: existing daily schedule; fresh success not audited; historical: 85 succeeded; structured: 6 complete; 0 partial; 6 failed; 69 captured observations | Earlier native audit: 500 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 6 complete; 0 partial; 6 failed; 69 captured observations. Record-bearing requested task envelope [2021-01-01, 2026-10-10); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q057) | Technical structured-task failures listed above; repair/retry while retaining committed pages. |
| 055 | EIA retail prices (`eia_retail_prices`) | Daily: existing daily schedule; fresh success not audited; historical: 31 succeeded; structured: 185 complete; 0 partial; 16 failed; 179 captured observations | Earlier native audit: 197 committed row occurrences; windows [2021-01-01, 2026-10-27); 2016-era coverage not established Current structured scheduler: 185 complete; 0 partial; 16 failed; 179 captured observations. Record-bearing requested task envelope [2017-05-01, 2026-09-01); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q055) | Technical structured-task failures listed above; repair/retry while retaining committed pages. |
| 056 | California ISO prices (`caiso_prices`) | Daily: existing daily schedule; fresh success not audited; historical: 41 succeeded/1 running; structured: 327 complete; 0 partial; 56 failed; 39,240 captured observations | Earlier native audit: 186,766 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 327 complete; 0 partial; 56 failed; 39,240 captured observations. Record-bearing requested task envelope [2023-07-01, 2024-01-07); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q056) | Technical structured-task failures listed above; repair/retry while retaining committed pages. |
| 147 | Zenodo research artifacts and usage (`zenodo_research_artifacts_and_usage`) | Daily: structured: 0 complete; 0 partial; 9 failed; 800 captured observations; historical: 42 succeeded/1 pending; structured: 8 complete; 13 partial; 89 failed; 2,650 captured observations | No committed structured-data evidence in earlier native audit. Current structured scheduler: 8 complete; 13 partial; 89 failed; 2,650 captured observations. Record-bearing requested task envelope [2016-01-01, 2016-01-22); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q147) | Technical structured-task failures listed above; repair/retry while retaining committed pages. |
| 145 | bioRxiv / medRxiv preprints (`biorxiv_medrxiv_preprints`) | Daily: structured: 4 complete; 0 partial; 0 failed; 2,109 captured observations; historical: 75 succeeded; structured: 14 complete; 202 partial; 44 failed; 99,185 captured observations | No committed structured-data evidence in earlier native audit. Current structured scheduler: 14 complete; 202 partial; 44 failed; 99,185 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q145) | Technical structured-task failures listed above; repair/retry while retaining committed pages. |
| 143 | DataCite dissertations, datasets, software and usage (`datacite_dissertations_datasets_software_and_usage`) | Daily: structured: 0 complete; 0 partial; 5 failed; 1,300 captured observations; historical: 55 succeeded; structured: 46 complete; 160 partial; 4 failed; 193,140 captured observations | No committed structured-data evidence in earlier native audit. Current structured scheduler: 46 complete; 160 partial; 4 failed; 193,140 captured observations. Record-bearing requested task envelope [2016-01-01, 2021-11-01); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q143) | Technical structured-task failures listed above; repair/retry while retaining committed pages. |
| 075 | Copernicus ERA5 / ERA5-Land (`copernicus_era5_era5_land`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Existing key/register entry; integration or access validation pending (top). |
| 066 | FRED / ALFRED series and vintages (`fred_alfred_series_and_vintages`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | NO rows in fresh preview — [SQL](#q066) | Existing key/register entry; integration or access validation pending (top). |
| 070 | Ember electricity demand and generation (`ember_electricity_demand_and_generation`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Existing key/register entry; integration or access validation pending (top). |
| 071 | WTO Timeseries API (`wto_timeseries_api`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Existing key/register entry; integration or access validation pending (top). |
| 072 | WTO Quantitative Restrictions API (`wto_quantitative_restrictions_api`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Existing key/register entry; integration or access validation pending (top). |
| 073 | WTO ePing SPS/TBT notifications (`wto_eping_sps_tbt_notifications`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Existing key/register entry; integration or access validation pending (top). |
| 098 | South Korea FSS OpenDART (`south_korea_fss_opendart`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | NO rows in fresh preview — [SQL](#q098) | Existing key/register entry; integration or access validation pending (top). |
| 118 | US Census International Trade API (`us_census_international_trade_api`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Existing key/register entry; integration or access validation pending (top). |
| 125 | USDA FAS Production, Supply and Distribution (`usda_fas_production_supply_and_distribution`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Existing key/register entry; integration or access validation pending (top). |
| 051 | UN Comtrade (`un_comtrade`) | Daily: existing daily schedule; fresh success not audited; historical: 20 succeeded; structured: 220 complete; 0 partial; 0 failed; 190 captured observations | Earlier native audit: 58 committed row occurrences; windows [2021-01-01, 2024-01-01); 2016-era coverage not established Current structured scheduler: 220 complete; 0 partial; 0 failed; 190 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-01-01); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q051) | Existing key/register entry; integration or access validation pending (top). |
| 008 | Japan EDINET corporate filings (`edinet_filings`) | Daily: existing daily schedule; fresh success not audited; historical: 34 succeeded; structured: 812 complete; 508 partial; 273 failed; 146,518 captured observations | Earlier native audit: 165,538 committed row occurrences; windows [2021-01-04, 2026-10-26); 2016-era coverage not established Current structured scheduler: 812 complete; 508 partial; 273 failed; 146,518 captured observations. Record-bearing requested task envelope [2021-01-04, 2023-02-07); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q008) | Technical structured-task failures listed above; repair/retry while retaining committed pages. |
| 020 | UK MHRA (`uk_mhra`) | Daily: existing daily schedule; fresh success not audited; historical: 116 succeeded | Earlier native audit: 13,355 committed row occurrences; windows [2021-01-01, 2026-10-16); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q020) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 019 | EMA medicines (`ema_medicines`) | Daily: existing daily schedule; fresh success not audited; historical: 1 succeeded; structured: 12 complete; 0 partial; 0 failed; 2,448 captured observations | Earlier native audit: 42,059 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 12 complete; 0 partial; 0 failed; 2,448 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q019) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 021 | Japan PMDA (`japan_pmda`) | Daily: existing daily schedule; fresh success not audited; historical: 15 succeeded | Earlier native audit: 2,950 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q021) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 026 | Europe PMC publication metadata (`europe_pmc`) | Daily: existing daily schedule; fresh success not audited; historical: 17 succeeded/1 pending; structured: 69 complete; 172 partial; 0 failed; 127,966 captured observations | Earlier native audit: 53,515 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 69 complete; 172 partial; 0 failed; 127,966 captured observations. Record-bearing requested task envelope [2016-01-01, 2023-04-01); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q026) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 027 | Europe PMC full text (`europe_pmc_fulltext`) | Daily: public: 0 files; 10 pages; 32 pending; 1 errors; historical: public: 0 files; 17 pages; 25 pending; 25 errors; 70 succeeded | Earlier native audit: 633 committed row occurrences; windows [2021-01-01, 2026-10-12); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 27 artifact metadata rows visible — [SQL](#q027) | Technical retrieval fixes listed above; no new key established. |
| 041 | USPTO assignment histories (`uspto_assignment_histories`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 116 committed row occurrences; windows [2023-01-01, 2026-10-23); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q041) | Audit/implement historical route and publication; no current enabled historical route established. |
| 007 | HKEX announcements (`hkex_news`) | Daily: public: 0 files; 1 pages; 0 pending; 0 errors; historical: public: 0 files; 1 pages; 0 pending; 0 errors; 1 succeeded | Earlier native audit: 67,909 committed row occurrences; windows [2020-12-31, 2026-10-14); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 2 artifact metadata rows visible — [SQL](#q007) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 011 | Finlight news (`finlight`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 34,970 committed row occurrences; windows [2021-01-01, 2026-10-22); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q011) | Audit/implement historical route and publication; no current enabled historical route established. |
| 014 | Personnel announcement archives (`personnel_archive`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 2,167 committed row occurrences; windows [2021-01-01, 2026-10-16); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q014) | Audit/implement historical route and publication; no current enabled historical route established. |
| 003 | EOD Historical Data market data (`eodhd_market`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 571,037 committed row occurrences; windows [2021-01-01, 2026-10-25); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q003) | Audit/implement historical route and publication; no current enabled historical route established. |
| 134 | X Ads Repository DSA API (`x_ads_repository_dsa_api`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Keys obtained; October 27 HTTP 402 credits and Ads Repository 403/453. Confirm intended product entitlement before spending. |
| 132 | TikTok Commercial Content API (`tiktok_commercial_content_api`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Key obtained; token succeeded October 27, content requests HTTP 500. Engineering retry; no replacement key request. |
| 001 | GLEIF legal entities (`gleif_legal_entities`) | Daily: public: 0 files; 11 pages; 118 pending; 0 errors; historical: public: 173 files; 197 pages; 999 pending; 26 errors; 67 succeeded | Earlier native audit: 156 committed row occurrences; windows [2026-10-09, 2026-10-24); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 381 artifact metadata rows visible — [SQL](#q001) | Technical retrieval fixes listed above; no new key established. |
| 002 | EOD Historical Data company profiles and listings (`eodhd`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 1,157,369 committed row occurrences; windows [2026-09-18, 2026-10-26); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q002) | Audit/implement historical route and publication; no current enabled historical route established. |
| 004 | HKEX prices (`hkex_prices`) | Daily: public: 0 files; 11 pages; 159 pending; 0 errors; historical: public: 53 files; 357 pages; 1209 pending; 4 errors; 69 succeeded | Earlier native audit: 17,644 committed row occurrences; windows [2026-09-23, 2026-09-24); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 421 artifact metadata rows visible — [SQL](#q004) | Technical retrieval fixes listed above; no new key established. |
| 005 | US SEC filings (including Form D and crowdfunding forms) (`sec_edgar`) | Daily: existing daily schedule; fresh success not audited; historical: 171 succeeded | Earlier native audit: 1,007,620 committed row occurrences; windows [2016-01-01, 2026-10-24) | YES — fresh preview returned rows — [SQL](#q005) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 006 | SEC company financial facts (`sec_companyfacts`) | Daily: existing daily schedule; fresh success not audited; historical: 9 succeeded; structured: 121 complete; 0 partial; 0 failed; 145,471 captured observations | Earlier native audit: 78,640 committed row occurrences; windows [2021-01-01, 2026-01-01); 2016-era coverage not established Current structured scheduler: 121 complete; 0 partial; 0 failed; 145,471 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q006) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 009 | Disclosure candidates (internal route) (`disclosure_candidates`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 1,394 committed row occurrences; windows [2021-01-04, 2026-10-15); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q009) | Audit/implement historical route and publication; no current enabled historical route established. |
| 010 | Disclosure documents (internal route) (`disclosure_documents`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 776 committed row occurrences; windows [2021-01-04, 2026-10-15); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q010) | Audit/implement historical route and publication; no current enabled historical route established. |
| 013 | People-related RSS feeds (`people_rss`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 16,980 committed row occurrences; windows [2021-01-01, 2026-10-27); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q013) | Audit/implement historical route and publication; no current enabled historical route established. |
| 015 | ClinicalTrials.gov (`clinicaltrials_gov`) | Daily: existing daily schedule; fresh success not audited; historical: 16 succeeded | Earlier native audit: 182,994 committed row occurrences; windows [2016-01-01, 2026-10-23) | YES — fresh preview returned rows — [SQL](#q015) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 016 | EMA Clinical Trials Information System (`ema_ctis`) | Daily: public: 0 files; 11 pages; 42 pending; 0 errors; historical: public: 0 files; 53 pages; 0 pending; 0 errors; 3 blocked/1 retryable_failed; 9 succeeded | Earlier native audit: 1,607 committed row occurrences; windows [2026-09-17, 2026-10-24); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 64 artifact metadata rows visible — [SQL](#q016) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 018 | Drugs@FDA applications (`drugsfda_applications`) | Daily: existing daily schedule; fresh success not audited; historical: 10 succeeded; structured: 130 complete; 0 partial; 0 failed; 42,991 captured observations | Earlier native audit: 19,026 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 130 complete; 0 partial; 0 failed; 42,991 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q018) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 022 | Health Canada notices of compliance (`canada_noc`) | Daily: existing daily schedule; fresh success not audited; historical: 1 succeeded; structured: 12 complete; 0 partial; 0 failed; 22,392 captured observations | Earlier native audit: 13,744 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 12 complete; 0 partial; 0 failed; 22,392 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q022) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 023 | Chinese Clinical Trial Registry (`chictr`) | Daily: public: 0 files; 1 pages; 19 pending; 10 errors; historical: public: 0 files; 1 pages; 19 pending; 19 errors; 71 succeeded | Earlier native audit: 93 committed row occurrences; windows [2026-09-17, 2026-09-18); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 2 artifact metadata rows visible — [SQL](#q023) | Technical retrieval fixes listed above; no new key established. |
| 025 | PubMed abstracts (`pubmed_abstracts`) | Daily: existing daily schedule; fresh success not audited; historical: 38 succeeded; structured: 390 complete; 0 partial; 0 failed; 85,441 captured observations | Earlier native audit: 26,304 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 390 complete; 0 partial; 0 failed; 85,441 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q025) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 028 | Crossref conference proceedings (`crossref_proceedings`) | Daily: public: 1 files; 0 pages; 0 pending; 0 errors; historical: public: 1 files; 0 pages; 0 pending; 0 errors; 1 succeeded | Earlier native audit: 2,603,004 committed row occurrences; windows [2021-01-01, 2026-10-25); 2016-era coverage not established; typed table also has 679,325 rows dated 2016-01-01–2026-10-26 by publication date; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 2 artifact metadata rows visible — [SQL](#q028) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 029 | CMS coverage policies (`cms_coverage`) | Daily: existing daily schedule; fresh success not audited; historical: 1 succeeded; structured: 12 complete; 0 partial; 0 failed; 104 captured observations | Earlier native audit: 4,947 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 12 complete; 0 partial; 0 failed; 104 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q029) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 030 | CMS coverage documents (`cms_coverage_documents`) | Daily: public: 0 files; 1 pages; 0 pending; 0 errors; historical: public: 0 files; 1 pages; 0 pending; 0 errors; 7 succeeded | Earlier native audit: 372 committed row occurrences; windows [2021-01-01, 2026-10-10); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 2 artifact metadata rows visible — [SQL](#q030) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 031 | CMS payments catalog and financial records (`cms_payments_catalog`) | Daily: public: 0 files; 1 pages; 0 pending; 0 errors; historical: public: 0 files; 1 pages; 0 pending; 0 errors; 1 succeeded | Earlier native audit: 680 committed row occurrences; windows [2026-10-09, 2026-10-24); 2016-era coverage not established; plus 76,013,225 bulk payments rows (2021–2025) and 63,336 drug-spending rows (edition years unverified); Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 2 artifact metadata rows visible — [SQL](#q031) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 032 | FDA Dashboard compliance actions (`fda_dd_compliance_actions`) | Daily: existing daily schedule; fresh success not audited; historical: 26 succeeded; structured: 131 complete; 0 partial; 0 failed; 134,238 captured observations | Earlier native audit: 80,564 committed row occurrences; windows [2021-01-01, 2026-10-27); 2016-era coverage not established Current structured scheduler: 131 complete; 0 partial; 0 failed; 134,238 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q032) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 033 | FDA Dashboard import refusals (`fda_dd_import_refusals`) | Daily: existing daily schedule; fresh success not audited; historical: 52 succeeded; structured: 131 complete; 0 partial; 0 failed; 213,603 captured observations | Earlier native audit: 199,147 committed row occurrences; windows [2021-01-01, 2026-10-27); 2016-era coverage not established Current structured scheduler: 131 complete; 0 partial; 0 failed; 213,603 captured observations. Record-bearing requested task envelope [2016-10-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q033) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 034 | FDA Dashboard inspection citations (`fda_dd_inspections_citations`) | Daily: existing daily schedule; fresh success not audited; historical: 20 succeeded/1 running; structured: 78 complete; 53 partial; 0 failed; 122,365 captured observations | Earlier native audit: 63,357 committed row occurrences; windows [2021-01-01, 2026-10-26); 2016-era coverage not established Current structured scheduler: 78 complete; 53 partial; 0 failed; 122,365 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q034) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 035 | FDA Dashboard inspection classifications (`fda_dd_inspections_classifications`) | Daily: existing daily schedule; fresh success not audited; historical: 79 succeeded; structured: 116 complete; 14 partial; 1 failed; 185,641 captured observations | Earlier native audit: 82,431 committed row occurrences; windows [2021-01-01, 2026-10-25); 2016-era coverage not established Current structured scheduler: 116 complete; 14 partial; 1 failed; 185,641 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q035) | Technical structured-task failures listed above; repair/retry while retaining committed pages. |
| 037 | FDA product codes (`fda_product_codes`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 1,246 committed row occurrences; windows [2026-10-11, 2026-10-25); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q037) | Audit/implement historical route and publication; no current enabled historical route established. |
| 038 | NIH RePORTER grants (`nih_reporter`) | Daily: existing daily schedule; fresh success not audited; historical: 64 succeeded; structured: 390 complete; 0 partial; 0 failed; 359,630 captured observations | Earlier native audit: 67,231 committed row occurrences; windows [2021-01-01, 2026-10-19); 2016-era coverage not established Current structured scheduler: 390 complete; 0 partial; 0 failed; 359,630 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q038) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 039 | Google Patents BigQuery (`google_patents_bigquery`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 5,540,316 committed row occurrences; windows [2021-01-01, 2026-09-23); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q039) | Audit/implement historical route and publication; no current enabled historical route established. |
| 040 | USPTO Open Data Portal (`uspto_odp`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 6,740,099 committed row occurrences; windows [2025-01-06, 2026-10-24); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q040) | Audit/implement historical route and publication; no current enabled historical route established. |
| 043 | USAspending federal awards (`usa_spending`) | Daily: existing daily schedule; fresh success not audited; historical: 78 succeeded/1 running; structured: 20 complete; 712 partial; 0 failed; 34,140 captured observations | Earlier native audit: 4,312 committed row occurrences; windows [2021-01-01, 2021-03-01); 2016-era coverage not established Current structured scheduler: 20 complete; 712 partial; 0 failed; 34,140 captured observations. Record-bearing requested task envelope [2016-01-01, 2021-03-01); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q043) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 045 | NIST robotics methods (`nist_robotics_methods`) | Daily: public: 0 files; 11 pages; 100 pending; 1 errors; historical: public: 2 files; 339 pages; 408 pending; 91 errors; 72 succeeded | Earlier native audit: 530 committed row occurrences; windows [2026-10-09, 2026-10-24); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 352 artifact metadata rows visible — [SQL](#q045) | Technical retrieval fixes listed above; no new key established. |
| 046 | MLPerf benchmark results (`mlperf_results`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 33,072 committed row occurrences; windows [2021-01-01, 2026-10-18); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q046) | Audit/implement historical route and publication; no current enabled historical route established. |
| 047 | CPSC recalls (`cpsc_recalls`) | Daily: existing daily schedule; fresh success not audited; historical: 10 succeeded; structured: 130 complete; 0 partial; 0 failed; 3,416 captured observations | Earlier native audit: 1,452 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 130 complete; 0 partial; 0 failed; 3,416 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q047) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 048 | Federal Register (`federal_register`) | Daily: existing daily schedule; fresh success not audited; historical: 7 blocked/1 pending; structured: 108 complete; 0 partial; 0 failed; 2,027 captured observations | Earlier native audit: 3,513 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 108 complete; 0 partial; 0 failed; 2,027 captured observations. Record-bearing requested task envelope [2016-01-01, 2022-11-01); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q048) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 049 | Trade screening lists (`trade_screening`) | Daily: public: 3 files; 8 pages; 76 pending; 0 errors; historical: public: 53 files; 87 pages; 1 pending; 1 errors; 71 succeeded | Earlier native audit: 444,362 committed row occurrences; windows [2026-10-09, 2026-10-24); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 151 artifact metadata rows visible — [SQL](#q049) | Technical retrieval fixes listed above; no new key established. |
| 052 | Department of Energy storage program (`doe_storage_program`) | Daily: public: 4 files; 8 pages; 16 pending; 0 errors; historical: public: 8 files; 23 pages; 1 pending; 1 errors; 72 succeeded | Earlier native audit: 813 committed row occurrences; windows [2026-10-09, 2026-10-24); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 43 artifact metadata rows visible — [SQL](#q052) | Technical retrieval fixes listed above; no new key established. |
| 053 | EIA battery generators (`eia_battery_generators`) | Daily: existing daily schedule; fresh success not audited; historical: 2 blocked/10 succeeded; structured: 129 complete; 0 partial; 0 failed; 82,938 captured observations | Earlier native audit: 76,933 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 129 complete; 0 partial; 0 failed; 82,938 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-01); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q053) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 054 | EIA generator index (`eia_generator_index`) | Daily: public: 11 files; 1 pages; 39 pending; 0 errors; historical: public: 274 files; 146 pages; 4580 pending; 0 errors; 70 succeeded | Earlier native audit: 2,148 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 432 artifact metadata rows visible — [SQL](#q054) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 058 | Research Organization Registry institutions (`ror_institutions`) | Daily: public: 1 files; 0 pages; 0 pending; 0 errors; historical: public: 1 files; 0 pages; 0 pending; 0 errors; 1 succeeded | Earlier native audit: 96 committed row occurrences; windows [2026-10-09, 2026-10-10); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 2 artifact metadata rows visible — [SQL](#q058) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 060 | DataForSEO search capture (`S65`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 6,464 search/trend/keyword-history sample rows; dated trend/history reaches 2021, search snapshots begin October 2026 | YES — fresh preview returned rows — [SQL](#q060) | Audit/implement historical route and publication; no current enabled historical route established. |
| 062 | SAM.gov opportunities (`sam_gov_opportunities`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 62,535 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q062) | Audit/implement historical route and publication; no current enabled historical route established. |
| 063 | USPTO Office Actions (`uspto_odp`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 2,920 committed row occurrences; windows [2021-01-01, 2026-10-21); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q063) | Audit/implement historical route and publication; no current enabled historical route established. |
| 064 | USPTO final Petition Decisions (`uspto_odp`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 3,999 committed row occurrences; windows [2021-01-04, 2026-10-25); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q064) | Audit/implement historical route and publication; no current enabled historical route established. |
| 065 | BIS SDMX API (`bis_sdmx_api`) | Daily: public: 1 files; 0 pages; 0 pending; 0 errors; historical: public: 1 files; 0 pages; 0 pending; 0 errors; 1 succeeded | Public route: BIS central-bank policy-rate daily CSV from 2016; selected dataflow only. No full 2016 coverage verified. | No structured Athena visibility established; 2 artifact metadata rows visible — [SQL](#q065) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 067 | UNIDO IIP and INDSTAT (`unido_iip_and_indstat`) | Daily: public: 2 files; 0 pages; 0 pending; 0 errors; historical: public: 2 files; 0 pages; 0 pending; 0 errors; 6 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 4 artifact metadata rows visible — [SQL](#q067) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 068 | ILOSTAT labor statistics (`ilostat_labor_statistics`) | Daily: public: 1 files; 0 pages; 0 pending; 0 errors; historical: public: 1 files; 0 pages; 0 pending; 0 errors; 1 succeeded | Public route: ILOSTAT annual unemployment-by-sex/age RDS snapshot. Original vintages and forecast/observation separation are not yet extracted. No full 2016 coverage verified. | No structured Athena visibility established; 2 artifact metadata rows visible — [SQL](#q068) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 069 | IMF PortWatch shipping activity (`imf_portwatch_shipping_activity`) | Daily: public: 0 files; 1 pages; 0 pending; 0 errors; historical: public: 0 files; 1 pages; 0 pending; 0 errors; 1 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 2 artifact metadata rows visible — [SQL](#q069) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 074 | EPO OPS patent legal events (`epo_ops_patent_legal_events`) | Daily: structured: 5 complete; 0 partial; 0 failed; 5 captured observations; historical: 4 succeeded/1 running; structured: 11 complete; 6 partial; 0 failed; 467 captured observations | No committed structured-data evidence in earlier native audit. Current structured scheduler: 11 complete; 6 partial; 0 failed; 467 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-26); not continuous coverage. | NO rows in fresh preview — [SQL](#q074) | Active collection; continue scoped backfill, legal-event refresh and publication verification. |
| 076 | NASA POWER weather and solar resource (`nasa_power_weather_and_solar_resource`) | Daily: structured: 8 complete; 0 partial; 0 failed; 56 captured observations; historical: 11 succeeded; structured: 88 complete; 0 partial; 0 failed; 31,608 captured observations | No committed structured-data evidence in earlier native audit. Current structured scheduler: 88 complete; 0 partial; 0 failed; 31,608 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q076) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 077 | USGS Earthquake Catalog API (`usgs_earthquakes`) | Daily: raw daily enabled; shared provider budget may defer; historical: 1975 succeeded; 1976 pending | 864,052 records in 1975 succeeded daily-query partitions; requested window envelope [2016-01-01, 2026-10-26). Not continuous coverage. | NO rows in fresh preview — [SQL](#q077) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 078 | UCDP organized violence (`ucdp_organized_violence`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Your action: follow up existing approval request (top). Public capture continues if listed. |
| 079 | arXiv early technical disclosures (`arxiv`) | Daily: raw daily enabled; shared provider budget may defer; historical: 1643 succeeded; 10 blocked; 1 running; 2297 pending | 874,952 records in 1643 succeeded daily-query partitions; requested window envelope [2016-01-01, 2026-10-26). Not continuous coverage. | NO rows in fresh preview — [SQL](#q079) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 080 | England NHSBSA prescribing data (`england_nhsbsa_prescribing_data`) | Daily: public: 1 files; 0 pages; 0 pending; 0 errors; historical: public: 1 files; 0 pages; 0 pending; 0 errors; 1 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 2 artifact metadata rows visible — [SQL](#q080) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 081 | Decodo shared web retrieval (access layer) (`decodo_shared_web_retrieval_access_layer`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Audit/implement historical route and publication; no current enabled historical route established. |
| 082 | SIA / WSTS public semiconductor sales (`sia_wsts_public_semiconductor_sales`) | Daily: public: 3 files; 4 pages; 10 pending; 4 errors; historical: public: 8 files; 22 pages; 6 pending; 6 errors; 66 succeeded | Public route: WSTS public regional monthly semiconductor billings workbook; detailed paid products are excluded. No full 2016 coverage verified. | No structured Athena visibility established; 37 artifact metadata rows visible — [SQL](#q082) | Technical retrieval fixes listed above; no new key established. |
| 083 | SEMI worldwide equipment billings (`semi_worldwide_equipment_billings`) | Daily: public: 0 files; 0 pages; 1 pending; 1 errors; historical: public: 0 files; 0 pages; 1 pending; 1 errors; 71 succeeded | Public route: Public press releases and report summaries only; licensed full historical datasets are excluded. No full 2016 coverage verified. | No structured Athena visibility established; no artifact rows returned by fresh inventory — [SQL](#q083) | Technical retrieval fixes listed above; no new key established. |
| 084 | International Federation of Robotics World Robotics (`international_federation_of_robotics_world_robotics`) | Daily: public: 10 files; 1 pages; 168 pending; 0 errors; historical: public: 181 files; 4 pages; 0 pending; 0 errors; 35 succeeded | Public route: Public press releases and report summaries only; licensed full historical datasets are excluded. No full 2016 coverage verified. | No structured Athena visibility established; 196 artifact metadata rows visible — [SQL](#q084) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 085 | IEA-PVPS solar deployment reports (`iea_pvps_solar_deployment_reports`) | Daily: public: 0 files; 12 pages; 51 pending; 0 errors; historical: public: 138 files; 123 pages; 0 pending; 0 errors; 44 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 273 artifact metadata rows visible — [SQL](#q085) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 086 | Germany G-BA drug benefit assessments (`germany_g_ba_drug_benefit_assessments`) | Daily: public: 1 files; 5 pages; 0 pending; 0 errors; historical: public: 1 files; 5 pages; 0 pending; 0 errors; 1 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 12 artifact metadata rows visible — [SQL](#q086) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 087 | France HAS medicine assessment opinions (`france_has_medicine_assessment_opinions`) | Daily: public: 0 files; 11 pages; 156 pending; 0 errors; historical: public: 0 files; 377 pages; 3733 pending; 0 errors; 68 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 388 artifact metadata rows visible — [SQL](#q087) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 089 | Canada CDA-AMC / CADTH reimbursement reviews (`canada_cda_amc_cadth_reimbursement_reviews`) | Daily: public: 0 files; 9 pages; 289 pending; 3 errors; historical: public: 0 files; 244 pages; 2294 pending; 168 errors; 67 succeeded/1 running | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 253 artifact metadata rows visible — [SQL](#q089) | Technical retrieval fixes listed above; no new key established. |
| 090 | France Assurance Maladie Open Medic (`france_assurance_maladie_open_medic`) | Daily: public: 0 files; 2 pages; 46 pending; 10 errors; historical: public: 1 files; 344 pages; 4655 pending; 39 errors; 64 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 347 artifact metadata rows visible — [SQL](#q090) | Technical retrieval fixes listed above; no new key established. |
| 091 | Japan MHLW NDB Open Data (`japan_mhlw_ndb_open_data`) | Daily: public: 3 files; 9 pages; 183 pending; 0 errors; historical: public: 3 files; 193 pages; 0 pending; 0 errors; 33 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 208 artifact metadata rows visible — [SQL](#q091) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 092 | CNINFO mainland-China company disclosures (`cninfo_mainland_china_company_disclosures`) | Daily: public: 0 files; 12 pages; 15 pending; 0 errors; historical: public: 0 files; 17 pages; 10 pending; 10 errors; 70 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 29 artifact metadata rows visible — [SQL](#q092) | Technical retrieval fixes listed above; no new key established. |
| 093 | China NBS industrial production (`china_nbs_industrial_production`) | Daily: public: 0 files; 10 pages; 7 pending; 1 errors; historical: public: 0 files; 16 pages; 1 pending; 1 errors; 71 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 26 artifact metadata rows visible — [SQL](#q093) | Technical retrieval fixes listed above; no new key established. |
| 094 | China MIIT electronics and battery statistics (`china_miit_electronics_and_battery_statistics`) | Daily: public: 0 files; 12 pages; 58 pending; 0 errors; historical: public: 4 files; 76 pages; 2 pending; 2 errors; 72 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 92 artifact metadata rows visible — [SQL](#q094) | Technical retrieval fixes listed above; no new key established. |
| 095 | China NEA power statistics (`china_nea_power_statistics`) | Daily: public: 0 files; 12 pages; 62 pending; 0 errors; historical: public: 15 files; 66 pages; 0 pending; 0 errors; 14 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 93 artifact metadata rows visible — [SQL](#q095) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 096 | China NHSA reimbursement and procurement (`china_nhsa_reimbursement_and_procurement`) | Daily: public: 0 files; 0 pages; 1 pending; 1 errors; historical: public: 34 files; 137 pages; 7 pending; 7 errors; 72 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 171 artifact metadata rows visible — [SQL](#q096) | Technical retrieval fixes listed above; no new key established. |
| 097 | China MOFCOM export controls (`china_mofcom_export_controls`) | Daily: public: 0 files; 12 pages; 28 pending; 0 errors; historical: public: 19 files; 34 pages; 0 pending; 0 errors; 9 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 65 artifact metadata rows visible — [SQL](#q097) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 099 | South Korea KOSIS statistical OpenAPI (`south_korea_kosis_statistical_openapi`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Your action: follow up existing approval request (top). Public capture continues if listed. |
| 100 | Taiwan TWSE/MOPS issuer and revenue archives (`taiwan_twse_mops_issuer_and_revenue_archives`) | Daily: public: 2 files; 0 pages; 0 pending; 0 errors; historical: public: 2 files; 0 pages; 0 pending; 0 errors; 1 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 4 artifact metadata rows visible — [SQL](#q100) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 101 | Taiwan customs trade statistics (`taiwan_customs_trade_statistics`) | Daily: public: 0 files; 0 pages; 1 pending; 1 errors; historical: public: 0 files; 0 pages; 1 pending; 1 errors; 69 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; no artifact rows returned by fresh inventory — [SQL](#q101) | Technical retrieval fixes listed above; no new key established. |
| 102 | India IBM mineral production (`india_ibm_mineral_production`) | Daily: public: 0 files; 0 pages; 1 pending; 1 errors; historical: public: 0 files; 0 pages; 1 pending; 1 errors; 72 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; no artifact rows returned by fresh inventory — [SQL](#q102) | Technical retrieval fixes listed above; no new key established. |
| 103 | Indonesia ESDM and Geological Agency mineral statistics (`indonesia_esdm_and_geological_agency_mineral_statistics`) | Daily: public: 10 files; 1 pages; 9 pending; 0 errors; historical: public: 26 files; 17 pages; 2 pending; 2 errors; 72 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 54 artifact metadata rows visible — [SQL](#q103) | Technical retrieval fixes listed above; no new key established. |
| 104 | Brazil ANM mineral yearbook (`brazil_anm_mineral_yearbook`) | Daily: public: 0 files; 0 pages; 1 pending; 1 errors; historical: public: 0 files; 0 pages; 1 pending; 1 errors; 71 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; no artifact rows returned by fresh inventory — [SQL](#q104) | Technical retrieval fixes listed above; no new key established. |
| 105 | Brazil ANM CFEM mining royalties (`brazil_anm_cfem_mining_royalties`) | Daily: public: 7 files; 1 pages; 14 pending; 4 errors; historical: public: 10 files; 2 pages; 10 pending; 10 errors; 72 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 20 artifact metadata rows visible — [SQL](#q105) | Technical retrieval fixes listed above; no new key established. |
| 106 | Brazil MDIC Comex Stat API (`brazil_mdic_comex_stat_api`) | Daily: public: 0 files; 0 pages; 1 pending; 1 errors; historical: public: 0 files; 0 pages; 1 pending; 1 errors; 71 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; no artifact rows returned by fresh inventory — [SQL](#q106) | Technical retrieval fixes listed above; no new key established. |
| 107 | Chile COCHILCO production and mining economics (`chile_cochilco_production_and_mining_economics`) | Daily: public: 0 files; 0 pages; 1 pending; 1 errors; historical: public: 0 files; 0 pages; 1 pending; 1 errors; 69 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; no artifact rows returned by fresh inventory — [SQL](#q107) | Technical retrieval fixes listed above; no new key established. |
| 108 | Chile SERNAGEOMIN mining yearbooks (`chile_sernageomin_mining_yearbooks`) | Daily: public: 0 files; 0 pages; 1 pending; 1 errors; historical: public: 0 files; 0 pages; 1 pending; 1 errors; 72 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; no artifact rows returned by fresh inventory — [SQL](#q108) | Technical retrieval fixes listed above; no new key established. |
| 109 | Chile SMA SNIFA environmental compliance (`chile_sma_snifa_environmental_compliance`) | Daily: public: 0 files; 1 pages; 0 pending; 0 errors; historical: public: 0 files; 1 pages; 0 pending; 0 errors; 1 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 2 artifact metadata rows visible — [SQL](#q109) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 110 | Peru MINEM mining bulletins and yearbooks (`peru_minem_mining_bulletins_and_yearbooks`) | Daily: public: 0 files; 11 pages; 36 pending; 1 errors; historical: public: 0 files; 133 pages; 1 pending; 1 errors; 65 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 144 artifact metadata rows visible — [SQL](#q110) | Technical retrieval fixes listed above; no new key established. |
| 111 | Argentina SIACAM mining indicators (`argentina_siacam_mining_indicators`) | Daily: public: 1 files; 1 pages; 0 pending; 0 errors; historical: public: 1 files; 1 pages; 0 pending; 0 errors; 1 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 4 artifact metadata rows visible — [SQL](#q111) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 112 | Brazil ANM SIGMINE and Cadastro Mineiro (`brazil_anm_sigmine_and_cadastro_mineiro`) | Daily: public: 0 files; 1 pages; 0 pending; 0 errors; historical: public: 0 files; 1 pages; 0 pending; 0 errors; 1 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 2 artifact metadata rows visible — [SQL](#q112) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 113 | Peru INGEMMET GEOCATMIN (`peru_ingemmet_geocatmin`) | Daily: public: 0 files; 0 pages; 1 pending; 1 errors; historical: public: 0 files; 0 pages; 1 pending; 1 errors; 71 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; no artifact rows returned by fresh inventory — [SQL](#q113) | Technical retrieval fixes listed above; no new key established. |
| 114 | ImportYeti shipment and supplier relationships (`importyeti_shipment_and_supplier_relationships`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Your decision: request API-enabled commercial access (top). |
| 115 | ImportGenius international shipments (`importgenius_international_shipments`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Your decision: request API-enabled commercial access (top). |
| 116 | MarineTraffic historical vessel tracks and port calls (`marinetraffic_historical_vessel_tracks_and_port_calls`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Your decision: request API-enabled commercial access (top). |
| 117 | Kpler commodity cargo flows (`kpler_commodity_cargo_flows`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Your decision: request API-enabled commercial access (top). |
| 119 | Eurostat Comext goods trade (`eurostat_comext_goods_trade`) | Daily: public: 0 files; 12 pages; 110 pending; 0 errors; historical: public: 71 files; 354 pages; 1776 pending; 1 errors; 71 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 437 artifact metadata rows visible — [SQL](#q119) | Technical retrieval fixes listed above; no new key established. |
| 120 | Climate TRACE industrial assets and activity (`climate_trace_industrial_assets_and_activity`) | Daily: public: 0 files; 4 pages; 0 pending; 0 errors; historical: public: 0 files; 4 pages; 0 pending; 0 errors; 1 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 8 artifact metadata rows visible — [SQL](#q120) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 121 | Open Supply Hub production locations (`open_supply_hub_production_locations`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Your action: obtain access/key (top). |
| 122 | OpenStreetMap / Overpass industrial facilities (`openstreetmap_overpass_industrial_facilities`) | Daily: public: 0 files; 0 pages; 1 pending; 1 errors; historical: public: 0 files; 0 pages; 1 pending; 1 errors; 65 succeeded | Public route: Named industrial facilities in a Phoenix reference bounding box, current OSM snapshot only; not global coverage or reconstructed 2016 facilities. No full 2016 coverage verified. | No structured Athena visibility established; no artifact rows returned by fresh inventory — [SQL](#q122) | Technical retrieval fixes listed above; no new key established. |
| 123 | Global Energy Monitor asset and ownership API (`global_energy_monitor_asset_and_ownership_api`) | Daily: public: 0 files; 1 pages; 0 pending; 0 errors; historical: public: 0 files; 1 pages; 0 pending; 0 errors; 1 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 2 artifact metadata rows visible — [SQL](#q123) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 124 | European Environment Agency industrial facilities (`european_environment_agency_industrial_facilities`) | Daily: public: 0 files; 11 pages; 2 pending; 1 errors; historical: public: 1 files; 11 pages; 1 pending; 1 errors; 72 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 23 artifact metadata rows visible — [SQL](#q124) | Technical retrieval fixes listed above; no new key established. |
| 126 | Brazil ABVE electric vehicle registrations (`brazil_abve_electric_vehicle_registrations`) | Daily: public: 0 files; 12 pages; 0 pending; 0 errors; historical: public: 0 files; 12 pages; 0 pending; 0 errors; 2 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 24 artifact metadata rows visible — [SQL](#q126) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 127 | Brazil SENATRAN vehicle fleet (`brazil_senatran_vehicle_fleet`) | Daily: public: 0 files; 1 pages; 0 pending; 0 errors; historical: public: 0 files; 1 pages; 0 pending; 0 errors; 1 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 2 artifact metadata rows visible — [SQL](#q127) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 128 | IEA Global EV Data Explorer and Outlook (`iea_global_ev_data_explorer_and_outlook`) | Daily: public: 0 files; 12 pages; 488 pending; 0 errors; historical: public: 0 files; 409 pages; 4591 pending; 1 errors; 68 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 421 artifact metadata rows visible — [SQL](#q128) | Technical retrieval fixes listed above; no new key established. |
| 129 | FAOSTAT food balances (`faostat_food_balances`) | Daily: public: 1 files; 0 pages; 0 pending; 0 errors; historical: public: 1 files; 0 pages; 0 pending; 0 errors; 1 succeeded | Public route: FAOSTAT normalized Food Balance Sheets bulk ZIP; year filtering and table extraction pending. No full 2016 coverage verified. | No structured Athena visibility established; 2 artifact metadata rows visible — [SQL](#q129) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 130 | Euromonitor Passport Statistics API (paid candidate) (`euromonitor_passport_statistics_api_paid_candidate`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Your decision: request API-enabled commercial access (top). |
| 131 | Meta Ad Library API (`meta_ad_library_api`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Your action: obtain access/key (top). |
| 133 | LinkedIn Ad Library / external API (`linkedin_ad_library_external_api`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Application submitted; await provider reply. |
| 135 | Sensor Tower / Pathmatics advertising intelligence (paid candidate) (`sensor_tower_pathmatics_advertising_intelligence_paid_candidate`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Your decision: request API-enabled commercial access (top). |
| 136 | Y Combinator company directory and cohorts (`y_combinator_company_directory_and_cohorts`) | Daily: public: 0 files; 1 pages; 0 pending; 0 errors; historical: public: 0 files; 1 pages; 0 pending; 0 errors; 1 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 2 artifact metadata rows visible — [SQL](#q136) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 137 | Techstars portfolio and cohorts (`techstars_portfolio_and_cohorts`) | Daily: public: 0 files; 1 pages; 0 pending; 0 errors; historical: public: 0 files; 1 pages; 0 pending; 0 errors; 1 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 2 artifact metadata rows visible — [SQL](#q137) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 138 | 500 Global portfolio and cohorts (`500_global_portfolio_and_cohorts`) | Daily: public: 0 files; 1 pages; 0 pending; 0 errors; historical: public: 0 files; 1 pages; 0 pending; 0 errors; 1 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 2 artifact metadata rows visible — [SQL](#q138) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 139 | Antler early-stage portfolio (`antler_early_stage_portfolio`) | Daily: public: 0 files; 2 pages; 0 pending; 0 errors; historical: public: 0 files; 2 pages; 0 pending; 0 errors; 1 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 4 artifact metadata rows visible — [SQL](#q139) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 140 | Dealroom startup and funding API (commercial) (`dealroom_startup_and_funding_api_commercial`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Your decision: request API-enabled commercial access (top). |
| 141 | Wefunder and Republic crowdfunding campaigns (`wefunder_and_republic_crowdfunding_campaigns`) | Daily: public: 0 files; 1 pages; 0 pending; 0 errors; historical: public: 0 files; 1 pages; 0 pending; 0 errors; 1 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 2 artifact metadata rows visible — [SQL](#q141) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 142 | OpenAlex scholarly graph (`openalex_scholarly_graph`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Your action: obtain access/key (top). |
| 144 | OpenAIRE Graph projects and research products (`openaire_graph_projects_and_research_products`) | Daily: public: 1 files; 0 pages; 0 pending; 0 errors; historical: public: 1 files; 0 pages; 0 pending; 0 errors; 1 succeeded | Public route: Public OpenAIRE project metadata sample. This capture does not yet paginate the full graph or assert historical completeness. No full 2016 coverage verified. | No structured Athena visibility established; 2 artifact metadata rows visible — [SQL](#q144) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 146 | Open Science Framework projects and preregistrations (`open_science_framework_projects_and_preregistrations`) | Daily: public: 1 files; 0 pages; 0 pending; 0 errors; historical: public: 1 files; 0 pages; 0 pending; 0 errors; 1 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 2 artifact metadata rows visible — [SQL](#q146) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 148 | Semantic Scholar citation context (`semantic_scholar_citation_context`) | Daily: public: 0 files; 0 pages; 1 pending; 1 errors; historical: public: 0 files; 0 pages; 1 pending; 1 errors; 66 succeeded | Public route: Public Semantic Scholar robotics keyword metadata sample, at most the first public result page. Full citation-context coverage needs a dedicated adapter and potentially a key. No full 2016 coverage verified. | No structured Athena visibility established; no artifact rows returned by fresh inventory — [SQL](#q148) | Technical retrieval fixes listed above; no new key established. |
| 149 | France theses.fr doctoral theses (`france_theses_fr_doctoral_theses`) | Daily: public: 0 files; 0 pages; 1 pending; 1 errors; historical: public: 0 files; 0 pages; 1 pending; 1 errors; 72 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; no artifact rows returned by fresh inventory — [SQL](#q149) | Technical retrieval fixes listed above; no new key established. |
| 150 | Brazil CAPES theses and dissertations (`brazil_capes_theses_and_dissertations`) | Daily: public: 0 files; 11 pages; 394 pending; 1 errors; historical: public: 149 files; 214 pages; 454 pending; 37 errors; 66 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 374 artifact metadata rows visible — [SQL](#q150) | Technical retrieval fixes listed above; no new key established. |
| 151 | NSF research awards API (`nsf_awards`) | Daily: raw daily enabled; shared provider budget may defer; historical: 364 succeeded; 30 blocked; 3557 pending | 8,374 records in 364 succeeded daily-query partitions; requested window envelope [2016-01-04, 2026-10-20). Not continuous coverage. | NO rows in fresh preview — [SQL](#q151) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 152 | European Commission CORDIS (`european_commission_cordis`) | Daily: public: 2 files; 0 pages; 0 pending; 0 errors; historical: public: 2 files; 0 pages; 0 pending; 0 errors; 1 succeeded | Public route: CORDIS H2020 and Horizon Europe public project CSV archives; pre-programme coverage is not asserted. No full 2016 coverage verified. | No structured Athena visibility established; 4 artifact metadata rows visible — [SQL](#q152) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 153 | Japan KAKEN funded research (`japan_kaken_funded_research`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Your action: obtain access/key (top). |
| 154 | Brazil FAPESP PIPE and grants (`brazil_fapesp_pipe_and_grants`) | Daily: public: 0 files; 12 pages; 24 pending; 0 errors; historical: public: 0 files; 51 pages; 1 pending; 1 errors; 71 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; 63 artifact metadata rows visible — [SQL](#q154) | Technical retrieval fixes listed above; no new key established. |
| 155 | UKRI Gateway to Research (`ukri_gateway_to_research`) | Daily: public: 0 files; 0 pages; 1 pending; 1 errors; historical: public: 0 files; 0 pages; 1 pending; 1 errors; 69 succeeded | Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | No structured Athena visibility established; no artifact rows returned by fresh inventory — [SQL](#q155) | Technical retrieval fixes listed above; no new key established. |
| 156 | Hugging Face Hub models and datasets (`hugging_face_hub_models_and_datasets`) | Daily: structured: 1 complete; 1 partial; 0 failed; 29,604 captured observations; historical: 43 succeeded/1 running; structured: 0 complete; 2 partial; 0 failed; 416,800 captured observations | No committed structured-data evidence in earlier native audit. Current structured scheduler: 0 complete; 2 partial; 0 failed; 416,800 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q156) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 157 | Altmetric scholarly attention (commercial) (`altmetric_scholarly_attention_commercial`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Your decision: request API-enabled commercial access (top). |
| 158 | University technology-transfer catalogs and reports (`university_technology_transfer_catalogs_and_reports`) | Daily: public: 10 files; 1 pages; 16 pending; 1 errors; historical: public: 25 files; 1 pages; 1 pending; 1 errors; 72 succeeded | Public route: Initial Stanford and MIT public technology-transfer report indexes only; broader universities require additional configured publisher URLs. No full 2016 coverage verified. | No structured Athena visibility established; 37 artifact metadata rows visible — [SQL](#q158) | Technical retrieval fixes listed above; no new key established. |
| 012 | Marketaux news (paused) (`marketaux`) | Daily: OWNER PAUSED; historical: OWNER PAUSED | Earlier native audit: 34,300 committed row occurrences; windows [2021-01-01, 2026-10-21); 2016-era coverage not established; OWNER PAUSE PRESERVED | YES — fresh preview returned rows — [SQL](#q012) | Owner pause preserved. |
| 044 | GitHub repositories and SDKs (paused) (`github_sdk`) | Daily: OWNER PAUSED; historical: OWNER PAUSED | Earlier native audit: 8,041 committed row occurrences; windows [2026-10-09, 2026-10-20); 2016-era coverage not established; OWNER PAUSE PRESERVED | YES — fresh preview returned rows — [SQL](#q044) | Owner pause preserved. |
| 059 | Reddit posts and comments (paused) (`reddit`) | Daily: OWNER PAUSED; historical: OWNER PAUSED | Earlier native audit: 4,099 Athena rows with creation dates 2021-01-19 through 2026-10-21; capture paused; OWNER PAUSE PRESERVED | YES — fresh preview returned rows — [SQL](#q059) | Owner pause preserved. |
| 061 | Bluesky posts (paused) (`bluesky_search`) | Daily: OWNER PAUSED; historical: OWNER PAUSED | Earlier native audit: 1,053 committed row occurrences; windows [2026-09-23, 2026-10-22); 2016-era coverage not established; OWNER PAUSE PRESERVED | YES — fresh preview returned rows — [SQL](#q061) | Owner pause preserved. |
| 088 | NICE technology appraisals (`nice_technology_appraisals`) | Daily: PAUSED — retained prior artifact evidence only; historical: PAUSED — NICE API licence/security approval required | Public route: NICE direct licensing clarification: AI use must use licensed syndication API after cybersecurity review; development documents excluded. No full 2016 coverage verified. Retained artifacts must not feed AI pending NICE approval. | No structured Athena visibility established; 2 artifact metadata rows visible — [SQL](#q088) | Owner action: NICE syndication application, certification/report review and licence. Exclude development documents from AI. |

## SQL to view each available source

Use **us-east-1** and the named workgroup. A LIMIT preview does not establish full history. Empty visibility checks are included for raw/new API sources that are not yet published.

### q001

**001. GLEIF legal entities**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('gleif_legal_entities')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 1
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q002

**002. EOD Historical Data company profiles and listings**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('eodhd')
  AND dataset IN ('company_profiles', 'listing_inventory')
LIMIT 1;
```

### q003

**003. EOD Historical Data market data**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('eodhd_market')
  AND dataset IN ('market_records')
LIMIT 1;
```

### q004

**004. HKEX prices**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('hkex_prices')
  AND dataset IN ('market_records')
LIMIT 1;
```

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 4
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q005

**005. US SEC filings (including Form D and crowdfunding forms)**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('sec_edgar')
  AND dataset IN ('filings')
LIMIT 1;
```

### q006

**006. SEC company financial facts**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('sec_companyfacts')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q007

**007. HKEX announcements**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('hkex_news')
  AND dataset IN ('filings')
LIMIT 1;
```

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 7
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q008

**008. Japan EDINET corporate filings**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('edinet_filings')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q009

**009. Disclosure candidates (internal route)**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('disclosure_candidates')
  AND dataset IN ('licensing_agreements', 'ma_announcements', 'press_releases', 'strategic_transactions')
LIMIT 1;
```

### q010

**010. Disclosure documents (internal route)**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('disclosure_documents')
  AND dataset IN ('documents')
LIMIT 1;
```

### q011

**011. Finlight news**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('finlight')
  AND dataset IN ('news_articles')
LIMIT 1;
```

### q012

**012. Marketaux news (paused)**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('marketaux')
  AND dataset IN ('news_articles')
LIMIT 1;
```

### q013

**013. People-related RSS feeds**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('people_rss')
  AND dataset IN ('people_source_records')
LIMIT 1;
```

### q014

**014. Personnel announcement archives**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('personnel_archive')
  AND dataset IN ('people_source_records')
LIMIT 1;
```

### q015

**015. ClinicalTrials.gov**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('clinicaltrials_gov')
  AND dataset IN ('research_records')
LIMIT 1;
```

### q016

**016. EMA Clinical Trials Information System**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('ema_ctis')
  AND dataset IN ('research_records')
LIMIT 1;
```

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 16
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q017

**017. FDA openFDA**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('fda_openfda')
  AND dataset IN ('research_records')
LIMIT 1;
```

### q018

**018. Drugs@FDA applications**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('drugsfda_applications')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q019

**019. EMA medicines**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('ema_medicines')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q020

**020. UK MHRA**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('uk_mhra')
  AND dataset IN ('research_records')
LIMIT 1;
```

### q021

**021. Japan PMDA**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('japan_pmda')
  AND dataset IN ('research_records')
LIMIT 1;
```

### q022

**022. Health Canada notices of compliance**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('canada_noc')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q023

**023. Chinese Clinical Trial Registry**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('chictr')
  AND dataset IN ('research_records')
LIMIT 1;
```

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 23
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q024

**024. NMPA trials**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('nmpa_trials')
  AND dataset IN ('registry_inventory', 'research_records')
LIMIT 1;
```

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 24
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q025

**025. PubMed abstracts**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('pubmed_abstracts')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q026

**026. Europe PMC publication metadata**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('europe_pmc')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q027

**027. Europe PMC full text**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('europe_pmc_fulltext')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 27
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q028

**028. Crossref conference proceedings**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('crossref_proceedings')
  AND dataset IN ('conference_records')
LIMIT 1;
```

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 28
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q029

**029. CMS coverage policies**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('cms_coverage')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q030

**030. CMS coverage documents**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('cms_coverage_documents')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 30
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q031

**031. CMS payments catalog and financial records**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('cms_payments_catalog')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 31
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q032

**032. FDA Dashboard compliance actions**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('fda_dd_compliance_actions')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q033

**033. FDA Dashboard import refusals**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('fda_dd_import_refusals')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q034

**034. FDA Dashboard inspection citations**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('fda_dd_inspections_citations')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q035

**035. FDA Dashboard inspection classifications**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('fda_dd_inspections_classifications')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q036

**036. FDA Enforcement Report recalls**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('fda_ires_recalls')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q037

**037. FDA product codes**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('fda_product_codes')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q038

**038. NIH RePORTER grants**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('nih_reporter', 'nih_grant_facts', 'nih_grant_lifecycles', 'nih_grant_publications', 'grant_institutions', 'grant_institution_links', 'grant_entity_connections')
LIMIT 1;
```

### q039

**039. Google Patents BigQuery**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('google_patents_bigquery')
  AND dataset IN ('patent_records')
LIMIT 1;
```

### q040

**040. USPTO Open Data Portal**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('uspto_odp')
  AND dataset IN ('patent_assignment_records', 'patent_records')
LIMIT 1;
```

### q041

**041. USPTO assignment histories**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('uspto_assignment_histories')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q042

**042. Tenders Electronic Daily procurement notices**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('ted_notices')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q043

**043. USAspending federal awards**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('usa_spending')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q044

**044. GitHub repositories and SDKs (paused)**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('github_sdk')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q045

**045. NIST robotics methods**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('nist_robotics_methods', 'nist_robotics_documents', 'nist_robotics_product_matches')
LIMIT 1;
```

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 45
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q046

**046. MLPerf benchmark results**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('mlperf_results')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q047

**047. CPSC recalls**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('cpsc_recalls')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q048

**048. Federal Register**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('federal_register', 'federal_register_documents')
LIMIT 1;
```

### q049

**049. Trade screening lists**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('trade_screening', 'trade_screening_enriched')
LIMIT 1;
```

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 49
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q050

**050. USGS minerals**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('usgs_minerals')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q051

**051. UN Comtrade**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('un_comtrade')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q052

**052. Department of Energy storage program**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('doe_storage_program', 'doe_storage_benchmarks', 'doe_storage_documents', 'doe_storage_funding')
LIMIT 1;
```

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 52
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q053

**053. EIA battery generators**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('eia_battery_generators')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q054

**054. EIA generator index**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('eia_generator_index')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 54
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q055

**055. EIA retail prices**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('eia_retail_prices')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q056

**056. California ISO prices**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('caiso_prices', 'caiso_ancillary_prices', 'caiso_archive_inventory', 'caiso_price_intervals', 'caiso_storage_indicators')
LIMIT 1;
```

### q057

**057. BLS wages**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('bls_wages')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q058

**058. Research Organization Registry institutions**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('ror_institutions')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 58
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q059

**059. Reddit posts and comments (paused)**

Structured data preview. Workgroup: `optima-social-research`.

```sql
SELECT record_id, subreddit, created_utc, observed_utc, verified_utc, source_url
FROM optima_social_research.reddit_records
WHERE created_utc >= 1451606400
LIMIT 1;
```

### q060

**060. DataForSEO search capture**

Structured data preview. Workgroup: `optima-eodhd-research`.

```sql
SELECT source_id,dataset,event_date,observed_at,source_url,payload_json
FROM optima_source_readiness.source_samples_windows
WHERE source_id='S65'
LIMIT 1;
```

### q061

**061. Bluesky posts (paused)**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('bluesky_search', 'bluesky_company_accounts', 'bluesky_company_posts', 'bluesky_company_events')
LIMIT 1;
```

### q062

**062. SAM.gov opportunities**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('sam_gov_opportunities')
  AND dataset IN ('specialist_inputs')
LIMIT 1;
```

### q063

**063. USPTO Office Actions**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('uspto_odp')
  AND dataset IN ('patent_office_actions')
LIMIT 1;
```

### q064

**064. USPTO final Petition Decisions**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source, dataset, record_id, ingested_at,
       json_extract_scalar(event_at_json, '$.value') AS event_date, source_url
FROM optima_collected_data.observations
WHERE source IN ('uspto_odp')
  AND dataset IN ('patent_petition_decisions')
LIMIT 1;
```

### q065

**065. BIS SDMX API**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 65
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q066

**066. FRED / ALFRED series and vintages**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source,dataset,record_id FROM optima_collected_data.observations WHERE source='fred_alfred_series_and_vintages' LIMIT 1;
```

### q067

**067. UNIDO IIP and INDSTAT**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 67
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q068

**068. ILOSTAT labor statistics**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 68
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q069

**069. IMF PortWatch shipping activity**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 69
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q074

**074. EPO OPS patent legal events**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source,dataset,record_id FROM optima_collected_data.observations WHERE source='epo_ops_patent_legal_events' LIMIT 1;
```

### q076

**076. NASA POWER weather and solar resource**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source,dataset,record_id FROM optima_collected_data.observations WHERE source='nasa_power_weather_and_solar_resource' LIMIT 1;
```

### q077

**077. USGS Earthquake Catalog API**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source,dataset,record_id,ingested_at FROM optima_collected_data.observations WHERE source='usgs_earthquakes' LIMIT 5;
```

### q079

**079. arXiv early technical disclosures**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source,dataset,record_id,ingested_at FROM optima_collected_data.observations WHERE source='arxiv' LIMIT 5;
```

### q080

**080. England NHSBSA prescribing data**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 80
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q082

**082. SIA / WSTS public semiconductor sales**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 82
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q083

**083. SEMI worldwide equipment billings**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 83
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q084

**084. International Federation of Robotics World Robotics**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 84
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q085

**085. IEA-PVPS solar deployment reports**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 85
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q086

**086. Germany G-BA drug benefit assessments**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 86
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q087

**087. France HAS medicine assessment opinions**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 87
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q088

**088. NICE technology appraisals**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 88
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q089

**089. Canada CDA-AMC / CADTH reimbursement reviews**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 89
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q090

**090. France Assurance Maladie Open Medic**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 90
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q091

**091. Japan MHLW NDB Open Data**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 91
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q092

**092. CNINFO mainland-China company disclosures**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 92
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q093

**093. China NBS industrial production**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 93
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q094

**094. China MIIT electronics and battery statistics**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 94
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q095

**095. China NEA power statistics**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 95
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q096

**096. China NHSA reimbursement and procurement**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 96
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q097

**097. China MOFCOM export controls**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 97
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q098

**098. South Korea FSS OpenDART**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source,dataset,record_id FROM optima_collected_data.observations WHERE source='south_korea_fss_opendart' LIMIT 1;
```

### q100

**100. Taiwan TWSE/MOPS issuer and revenue archives**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 100
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q101

**101. Taiwan customs trade statistics**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 101
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q102

**102. India IBM mineral production**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 102
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q103

**103. Indonesia ESDM and Geological Agency mineral statistics**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 103
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q104

**104. Brazil ANM mineral yearbook**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 104
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q105

**105. Brazil ANM CFEM mining royalties**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 105
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q106

**106. Brazil MDIC Comex Stat API**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 106
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q107

**107. Chile COCHILCO production and mining economics**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 107
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q108

**108. Chile SERNAGEOMIN mining yearbooks**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 108
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q109

**109. Chile SMA SNIFA environmental compliance**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 109
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q110

**110. Peru MINEM mining bulletins and yearbooks**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 110
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q111

**111. Argentina SIACAM mining indicators**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 111
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q112

**112. Brazil ANM SIGMINE and Cadastro Mineiro**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 112
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q113

**113. Peru INGEMMET GEOCATMIN**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 113
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q119

**119. Eurostat Comext goods trade**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 119
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q120

**120. Climate TRACE industrial assets and activity**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 120
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q122

**122. OpenStreetMap / Overpass industrial facilities**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 122
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q123

**123. Global Energy Monitor asset and ownership API**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 123
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q124

**124. European Environment Agency industrial facilities**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 124
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q126

**126. Brazil ABVE electric vehicle registrations**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 126
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q127

**127. Brazil SENATRAN vehicle fleet**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 127
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q128

**128. IEA Global EV Data Explorer and Outlook**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 128
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q129

**129. FAOSTAT food balances**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 129
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q136

**136. Y Combinator company directory and cohorts**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 136
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q137

**137. Techstars portfolio and cohorts**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 137
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q138

**138. 500 Global portfolio and cohorts**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 138
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q139

**139. Antler early-stage portfolio**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 139
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q141

**141. Wefunder and Republic crowdfunding campaigns**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 141
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q143

**143. DataCite dissertations, datasets, software and usage**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source,dataset,record_id FROM optima_collected_data.observations WHERE source='datacite_dissertations_datasets_software_and_usage' LIMIT 1;
```

### q144

**144. OpenAIRE Graph projects and research products**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 144
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q145

**145. bioRxiv / medRxiv preprints**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source,dataset,record_id FROM optima_collected_data.observations WHERE source='biorxiv_medrxiv_preprints' LIMIT 1;
```

### q146

**146. Open Science Framework projects and preregistrations**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 146
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q147

**147. Zenodo research artifacts and usage**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source,dataset,record_id FROM optima_collected_data.observations WHERE source='zenodo_research_artifacts_and_usage' LIMIT 1;
```

### q148

**148. Semantic Scholar citation context**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 148
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q149

**149. France theses.fr doctoral theses**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 149
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q150

**150. Brazil CAPES theses and dissertations**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 150
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q151

**151. NSF research awards API**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source,dataset,record_id,ingested_at FROM optima_collected_data.observations WHERE source='nsf_awards' LIMIT 5;
```

### q152

**152. European Commission CORDIS**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 152
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q154

**154. Brazil FAPESP PIPE and grants**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 154
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q155

**155. UKRI Gateway to Research**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 155
ORDER BY retrieved_at DESC
LIMIT 25;
```

### q156

**156. Hugging Face Hub models and datasets**

Structured data preview. Workgroup: `optima-collected-data`.

```sql
SELECT source,dataset,record_id FROM optima_collected_data.observations WHERE source='hugging_face_hub_models_and_datasets' LIMIT 1;
```

### q158

**158. University technology-transfer catalogs and reports**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT catalog_entry,source,mode,artifact_kind,retrieved_at,artifact_uri,bytes,sha256,scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE catalog_entry = 158
ORDER BY retrieved_at DESC
LIMIT 25;
```

## Earlier detailed native audit

The following retained counts and windows belong to the morning audit, not this refresh. Current execution/visibility is given above.

## Specialized Athena tables and important publication differences

These queries were executed successfully during the earlier audit; row counts refer to these typed tables, rather than the versioned shared observations table.

### market-range

Workgroup: `optima-market-research`. Query ID: `dc47529c-5a17-43d7-9dd3-1fe1a1f32853`.

```sql
SELECT source,min(event_date) AS first_date,max(event_date) AS last_date,count(*) AS rows_since_2016 FROM optima_market_research.market_prices_windows WHERE event_date>='2016-01-01' GROUP BY source;
```

| source | first_date | last_date | rows_since_2016 |
|---|---|---|---|
| eodhd_market | 2021-01-04 | 2026-10-23 | 484172 |
| hkex_prices | 2026-09-23 | 2026-09-23 | 17644 |

### news-range

Workgroup: `optima-news-research`. Query ID: `db0c20c7-763e-4853-8c70-f488b5f10e1c`.

```sql
SELECT source,min(published_at) AS first_date,max(published_at) AS last_date,count(*) AS rows_since_2016 FROM optima_news_research.news_articles_windows WHERE published_at>='2016-01-01' GROUP BY source;
```

| source | first_date | last_date | rows_since_2016 |
|---|---|---|---|
| marketaux | 2021-01-01T01:06:00+00:00 | 2026-10-11T23:55:20+00:00 | 15592 |
| finlight | 2021-01-04T03:03:09+00:00 | 2026-10-16T23:58:56+00:00 | 8415 |

### conference-range

Workgroup: `optima-collected-data`. Query ID: `402cc715-b1e7-450c-a2fa-4db35866ed7c`.

```sql
SELECT min(publication_date) AS first_date,max(publication_date) AS last_date,count(*) AS rows_since_2016 FROM optima_conference_research.conference_observations_windows WHERE publication_date>='2016-01-01' AND publication_date<=CAST(CURRENT_DATE AS varchar);
```

| first_date | last_date | rows_since_2016 |
|---|---|---|
| 2016-01-01 | 2026-10-26 | 679325 |

### global-patents-range

Workgroup: `optima-patent-research`. Query ID: `948b6578-3d48-4c2f-95a3-71e7c0c1fe6d`.

```sql
SELECT min(publication_date) AS first_date,max(publication_date) AS last_date,count(*) AS rows_since_2016 FROM optima_patent_research.patent_backfill_publications WHERE publication_date>=DATE '2016-01-01';
```

| first_date | last_date | rows_since_2016 |
|---|---|---|
| 2021-01-01 | 2026-09-17 | 5296699 |

### profile-count

Workgroup: `optima-eodhd-research`. Query ID: `e7c182f0-250c-4047-a305-a8bcd09400bf`.

```sql
SELECT count(*) AS rows,min(ingested_at) AS first_capture,max(ingested_at) AS latest_capture FROM optima_eodhd_research.company_profiles;
```

| rows | first_capture | latest_capture |
|---|---|---|
| 9438 | 2026-09-18T16:00:29.934200Z | 2026-09-22T17:44:53.041840Z |

### listing-count

Workgroup: `optima-eodhd-research`. Query ID: `d1f16c51-ac71-421b-acfd-44361eaa4e49`.

```sql
SELECT count(*) AS rows,min(inventory_observed_at) AS first_capture,max(inventory_observed_at) AS latest_capture FROM optima_eodhd_research.listing_inventory;
```

| rows | first_capture | latest_capture |
|---|---|---|
| 141783 | 2026-09-22T16:32:56.507936Z | 2026-09-22T16:36:38.181517Z |

### cms-editions

Workgroup: `optima-collected-data`. Query ID: `43382141-42d7-4a0e-a451-4649f7d968d9`.

```sql
SELECT source,category,min(program_year) AS first_year,max(program_year) AS last_year,count(*) AS editions,sum(row_count) AS edition_rows FROM optima_collected_data.cms_financial_editions GROUP BY source,category;
```

| source | category | first_year | last_year | editions | edition_rows |
|---|---|---|---|---|---|
| cms_open_payments | ownership | 2021 | 2025 | 5 | 20245 |
| cms_open_payments | research | 2021 | 2025 | 5 | 4747581 |
| cms_drug_spending | quarterly | unknown | unknown | 2 | 29490 |
| cms_open_payments | general | 2021 | 2025 | 5 | 71245399 |
| cms_drug_spending | annual | unknown | unknown | 3 | 33846 |

### cms-open-payments-count

Workgroup: `optima-collected-data`. Query ID: `dd6828db-20e7-4d14-a564-0a4e9a18a9cb`.

```sql
SELECT edition_id,count(*) AS rows FROM optima_collected_data.cms_open_payments_rows GROUP BY edition_id;
```

**76,013,225 rows** across 15 edition partitions. Individual edition counts are preserved in the JSON evidence.

### cms-drug-spending-count

Workgroup: `optima-collected-data`. Query ID: `83b3ee6b-c9e8-46d0-b556-5b4638f997d0`.

```sql
SELECT edition_id,count(*) AS rows FROM optima_collected_data.cms_drug_spending_rows GROUP BY edition_id;
```

**63,336 rows** across 5 edition partitions. Individual edition counts are preserved in the JSON evidence.

The CMS payments editions cover program years 2021–2025. Their catalog rows are not the underlying payments; the bulk row counts above come from live Athena queries. Drug-spending edition metadata lacks a program-year value, so a year span is not inferred. For raw row contents, filter one returned `edition_id` and select `row_json` from the matching bulk table with a small LIMIT.

Profiles/listing typed tables are older curated subsets of the shared observation history. To inspect all captured versions, use Q002. Publication lag and version selection explain why typed-table counts differ from the shared receipt; the report does not treat them as interchangeable.

## Expanded dataset breakdowns

### 002. EOD Historical Data company profiles and listings

| Stored source / dataset | Distinct-batch row occurrences | Captured requested windows, end exclusive |
|---|---:|---|
| `eodhd` / `company_profiles` | 142,558 | [2026-09-18, 2026-10-26) |
| `eodhd` / `listing_inventory` | 1,014,811 | [2026-09-18, 2026-10-26) |

### 009. Disclosure candidates (internal route)

| Stored source / dataset | Distinct-batch row occurrences | Captured requested windows, end exclusive |
|---|---:|---|
| `disclosure_candidates` / `licensing_agreements` | 123 | [2021-01-04, 2026-10-09) |
| `disclosure_candidates` / `ma_announcements` | 381 | [2021-01-04, 2026-10-15) |
| `disclosure_candidates` / `press_releases` | 429 | [2021-01-04, 2026-10-15) |
| `disclosure_candidates` / `strategic_transactions` | 461 | [2021-01-04, 2026-10-15) |

### 024. NMPA trials

| Stored source / dataset | Distinct-batch row occurrences | Captured requested windows, end exclusive |
|---|---:|---|
| `nmpa_trials` / `registry_inventory` | 28,854 | [2026-09-22, 2026-09-23) |
| `nmpa_trials` / `research_records` | 36,343 | [2021-01-01, 2026-10-16) |

### 038. NIH RePORTER grants

| Stored source / dataset | Distinct-batch row occurrences | Captured requested windows, end exclusive |
|---|---:|---|
| `grant_entity_connections` / `specialist_inputs` | 11,862 | [2026-10-18, 2026-10-19) |
| `grant_institution_links` / `specialist_inputs` | 11,862 | [2026-10-18, 2026-10-19) |
| `grant_institutions` / `specialist_inputs` | 541 | [2026-10-18, 2026-10-19) |
| `nih_grant_facts` / `specialist_inputs` | 11,862 | [2026-10-18, 2026-10-19) |
| `nih_grant_lifecycles` / `specialist_inputs` | 1,166 | [2026-10-18, 2026-10-19) |
| `nih_grant_publications` / `specialist_inputs` | 1,165 | [2026-10-18, 2026-10-19) |
| `nih_reporter` / `specialist_inputs` | 28,773 | [2021-01-01, 2026-10-16) |

### 040. USPTO Open Data Portal

| Stored source / dataset | Distinct-batch row occurrences | Captured requested windows, end exclusive |
|---|---:|---|
| `uspto_odp` / `patent_assignment_records` | 23 | [2026-09-22, 2026-09-24) |
| `uspto_odp` / `patent_records` | 6,740,076 | [2025-01-06, 2026-10-24) |

### 045. NIST robotics methods

| Stored source / dataset | Distinct-batch row occurrences | Captured requested windows, end exclusive |
|---|---:|---|
| `nist_robotics_documents` / `specialist_inputs` | 280 | [2026-10-18, 2026-10-23) |
| `nist_robotics_methods` / `specialist_inputs` | 16 | [2026-10-09, 2026-10-24) |
| `nist_robotics_product_matches` / `specialist_inputs` | 234 | [2026-10-18, 2026-10-20) |

### 048. Federal Register

| Stored source / dataset | Distinct-batch row occurrences | Captured requested windows, end exclusive |
|---|---:|---|
| `federal_register` / `specialist_inputs` | 2,946 | [2021-01-01, 2026-10-24) |
| `federal_register_documents` / `specialist_inputs` | 567 | [2022-02-01, 2026-10-24) |

### 049. Trade screening lists

| Stored source / dataset | Distinct-batch row occurrences | Captured requested windows, end exclusive |
|---|---:|---|
| `trade_screening` / `specialist_inputs` | 392,054 | [2026-10-09, 2026-10-24) |
| `trade_screening_enriched` / `specialist_inputs` | 52,308 | [2026-10-18, 2026-10-20) |

### 052. Department of Energy storage program

| Stored source / dataset | Distinct-batch row occurrences | Captured requested windows, end exclusive |
|---|---:|---|
| `doe_storage_benchmarks` / `specialist_inputs` | 247 | [2026-10-18, 2026-10-19) |
| `doe_storage_documents` / `specialist_inputs` | 335 | [2026-10-18, 2026-10-19) |
| `doe_storage_funding` / `specialist_inputs` | 214 | [2026-10-18, 2026-10-19) |
| `doe_storage_program` / `specialist_inputs` | 17 | [2026-10-09, 2026-10-24) |

### 056. California ISO prices

| Stored source / dataset | Distinct-batch row occurrences | Captured requested windows, end exclusive |
|---|---:|---|
| `caiso_ancillary_prices` / `specialist_inputs` | 71,042 | [2021-01-01, 2026-10-21) |
| `caiso_archive_inventory` / `specialist_inputs` | 1,270 | [2021-01-01, 2026-10-21) |
| `caiso_price_intervals` / `specialist_inputs` | 102,848 | [2021-01-01, 2026-10-21) |
| `caiso_prices` / `specialist_inputs` | 10,080 | [2023-07-01, 2026-10-24) |
| `caiso_storage_indicators` / `specialist_inputs` | 1,526 | [2021-01-01, 2026-10-21) |

### 061. Bluesky posts (paused)

| Stored source / dataset | Distinct-batch row occurrences | Captured requested windows, end exclusive |
|---|---:|---|
| `bluesky_company_accounts` / `specialist_inputs` | 13 | [2026-10-21, 2026-10-22) |
| `bluesky_search` / `social_records` | 1,040 | [2026-09-23, 2026-10-05) |



## Evidence, limits and gap policy

- Current queue/S3/Athena reads: `2026-10-26T20:22:59.865479+00:00` through `2026-10-26T20:25:06.278577+00:00` UTC. Evidence: [current-source-evidence.json](data-collection-processing/constellation/status/current-source-evidence.json).
- Public states snapshot: **2026-10-26 21:24:43 CET**; [public-source-rollout-2026-10-26.md](public-source-rollout-2026-10-26.md).
- Prior native final-manifest audit and baseline row counts: [native-manifest-audit.json](data-collection-processing/constellation/status/native-manifest-audit.json). Earlier publication counts are not current totals.
- Fresh bounded Athena preview query IDs/results and artifact inventory query ID are in the current evidence file. A successful preview proves visibility of a sample only.
- Key fields/status: [apiKeyRegister.md](apiKeyRegister.md); earlier credential-presence and endpoint probes are retained under `data-collection-processing/constellation/expansion/`. Key presence is not retested by printing or exposing secrets.
- Resize/worker limits: [resize record](data-collection-processing/constellation/expansion/resize-2026-10-26.md). Resource samples are short observations, not a sustained benchmark.

**Gap rule:** record every verified dated gap. Flag gaps **longer than five days** in the existing 24-hour checkup email; gaps of five days or less are record-only. Unprocessed backlog, healthy pagination and unverified date coverage are not classified as proven gaps.
