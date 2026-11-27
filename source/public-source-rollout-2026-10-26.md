# Public-source collection rollout

Updated **2026-11-27 12:13:16 CET**. This file refreshes every five minutes from S3 evidence.

**Collection controls:** historical enabled; daily capture enabled on t3.

**Placement:** daily capture on t3; historical worker m6a.xlarge. 15 configured workers share a 4-CPU / 6-GiB cap.

**Configured:** 106 public archive/document routes, 15 structured API collectors, and daily capture for the three already-running raw historical sources (USGS, NSF and arXiv). EPO OPS uses its stored credentials; the other new structured API routes are public. Paused archive rows remain visible as retained evidence; Decodo uses the existing credential.

**Observed:** 74/106 archive sources attempted by daily capture; 74/106 attempted by historical retrieval. 72 have saved at least one artifact; 52 have downloaded at least one non-HTML file. Errors below remain incomplete and retryable.

**Scope:** archive pages are discovery evidence. Downloaded files are raw captures. Neither establishes a complete structured dataset, coverage since 2016, original historical vintages, or Athena access to the file contents. Report summaries are distinct from licensed full products. API documentation/catalog captures are labelled metadata/discovery until a dataset adapter or resource downloader is implemented.

## Public archives and downloads

| # | Source | Daily on t3 | Historical on c7i | Current error codes |
|---|---|---|---|---|
| 1 | GLEIF legal entities | 0 files; 12 pages; 118 pending; 0 errors | 610 files; 678 pages; 81 pending; 81 errors | public_http_404, unreviewed_public_redirect |
| 4 | HKEX prices | 11 files; 1 pages; 30 pending; 0 errors | 1 files; 1 pages; 0 pending; 0 errors | none |
| 7 | HKEX announcements | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 16 | EMA Clinical Trials Information System | 0 files; 12 pages; 41 pending; 0 errors | 0 files; 53 pages; 0 pending; 0 errors | none |
| 23 | Chinese Clinical Trial Registry | 0 files; 1 pages; 19 pending; 11 errors | 0 files; 1 pages; 19 pending; 19 errors | public_http_405 |
| 24 | NMPA trials | 0 files; 1 pages; 1 pending; 1 errors | 0 files; 1 pages; 2 pending; 2 errors | public_http_202 |
| 27 | Europe PMC full text | 0 files; 7 pages; 35 pending; 5 errors | 0 files; 17 pages; 25 pending; 25 errors | SourceIssue, scrape_incomplete_response, scrape_target_http_404 |
| 28 | Crossref conference proceedings | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 30 | CMS coverage documents | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 31 | CMS payments catalog and financial records | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 45 | NIST robotics methods | 0 files; 11 pages; 100 pending; 1 errors | 2 files; 589 pages; 158 pending; 158 errors | public_http_405 |
| 49 | Trade screening lists | 4 files; 8 pages; 75 pending; 0 errors | 54 files; 87 pages; 0 pending; 0 errors | none |
| 52 | Department of Energy storage program | 2 files; 8 pages; 50 pending; 2 errors | 27 files; 97 pages; 10 pending; 10 errors | public_http_404, scrape_gateway_http_400 |
| 54 | EIA generator index | 10 files; 1 pages; 0 pending; 0 errors | 10 files; 1 pages; 0 pending; 0 errors | none |
| 58 | Research Organization Registry institutions | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 65 | BIS SDMX API | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 67 | UNIDO IIP and INDSTAT | 2 files; 0 pages; 0 pending; 0 errors | 2 files; 0 pages; 0 pending; 0 errors | none |
| 68 | ILOSTAT labor statistics | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 69 | IMF PortWatch shipping activity | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 80 | England NHSBSA prescribing data | PAUSED — retained prior evidence only | PAUSED — retained prior evidence only | none |
| 82 | SIA / WSTS public semiconductor sales | 2 files; 1 pages; 0 pending; 0 errors | 2 files; 1 pages; 0 pending; 0 errors | none |
| 83 | SEMI worldwide equipment billings | 4 files; 1 pages; 0 pending; 0 errors | 4 files; 1 pages; 0 pending; 0 errors | none |
| 84 | International Federation of Robotics World Robotics | 1 files; 11 pages; 31 pending; 0 errors | 43 files; 41 pages; 0 pending; 0 errors | none |
| 85 | IEA-PVPS solar deployment reports | 6 files; 6 pages; 10 pending; 0 errors | 11 files; 13 pages; 0 pending; 0 errors | none |
| 86 | Germany G-BA drug benefit assessments | 1 files; 11 pages; 62 pending; 0 errors | 1512 files; 887 pages; 17 pending; 17 errors | public_asset_too_large |
| 87 | France HAS medicine assessment opinions | 6 files; 6 pages; 4988 pending; 0 errors | 7 files; 4993 pages; 0 pending; 0 errors | none |
| 88 | NICE technology appraisals | PAUSED — retained prior evidence only | PAUSED — retained prior evidence only | none |
| 89 | Canada CDA-AMC / CADTH reimbursement reviews | 0 files; 4 pages; 4 pending; 4 errors | 4 files; 4 pages; 0 pending; 0 errors | SourceIssue |
| 90 | France Assurance Maladie Open Medic | 1 files; 11 pages; 57 pending; 0 errors | 6 files; 31 pages; 192 pending; 192 errors | openmedic_unreviewed_file |
| 91 | Japan MHLW NDB Open Data | 2 files; 2 pages; 424 pending; 0 errors | 2166 files; 13 pages; 0 pending; 0 errors | none |
| 92 | CNINFO mainland-China company disclosures | PAUSED — retained prior evidence only | PAUSED — retained prior evidence only | unreviewed_public_redirect |
| 93 | China NBS industrial production | 1 files; 11 pages; 3 pending; 0 errors | 2 files; 14 pages; 0 pending; 0 errors | none |
| 94 | China MIIT electronics and battery statistics | 1 files; 11 pages; 10 pending; 0 errors | 1 files; 21 pages; 0 pending; 0 errors | none |
| 95 | China NEA power statistics | 3 files; 1 pages; 0 pending; 0 errors | 2 files; 1 pages; 0 pending; 0 errors | none |
| 96 | China NHSA reimbursement and procurement | 5 files; 1 pages; 0 pending; 0 errors | 5 files; 1 pages; 0 pending; 0 errors | none |
| 97 | China MOFCOM export controls | 1 files; 11 pages; 7 pending; 0 errors | 1 files; 72 pages; 0 pending; 0 errors | none |
| 100 | Taiwan TWSE/MOPS issuer and revenue archives | 2 files; 0 pages; 0 pending; 0 errors | 2 files; 0 pages; 0 pending; 0 errors | none |
| 101 | Taiwan customs trade statistics | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 102 | India IBM mineral production | 8 files; 1 pages; 0 pending; 0 errors | 104 files; 11 pages; 0 pending; 0 errors | none |
| 103 | Indonesia ESDM and Geological Agency mineral statistics | 1 files; 3 pages; 7 pending; 0 errors | 27 files; 33 pages; 0 pending; 0 errors | none |
| 104 | Brazil ANM mineral yearbook | 11 files; 1 pages; 16 pending; 0 errors | 27 files; 1 pages; 0 pending; 0 errors | none |
| 105 | Brazil ANM CFEM mining royalties | 1 files; 0 pages; 0 pending; 0 errors | 3 files; 0 pages; 0 pending; 0 errors | none |
| 106 | Brazil MDIC Comex Stat API | 2 files; 0 pages; 0 pending; 0 errors | 22 files; 0 pages; 0 pending; 0 errors | none |
| 107 | Chile COCHILCO production and mining economics | 3 files; 1 pages; 32 pending; 0 errors | 35 files; 1 pages; 0 pending; 0 errors | none |
| 108 | Chile SERNAGEOMIN mining yearbooks | 3 files; 1 pages; 16 pending; 0 errors | 18 files; 1 pages; 0 pending; 0 errors | none |
| 109 | Chile SMA SNIFA environmental compliance | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 110 | Peru MINEM mining bulletins and yearbooks | 1 files; 3 pages; 54 pending; 0 errors | 229 files; 237 pages; 0 pending; 0 errors | none |
| 111 | Argentina SIACAM mining indicators | 2 files; 0 pages; 1 pending; 1 errors | 3 files; 0 pages; 0 pending; 0 errors | ConnectTimeout |
| 112 | Brazil ANM SIGMINE and Cadastro Mineiro | 2 files; 2 pages; 39 pending; 0 errors | 2 files; 0 pages; 0 pending; 0 errors | none |
| 113 | Peru INGEMMET GEOCATMIN | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 119 | Eurostat Comext goods trade | 8 files; 0 pages; 0 pending; 0 errors | 8 files; 0 pages; 0 pending; 0 errors | none |
| 120 | Climate TRACE industrial assets and activity | 5 files; 0 pages; 0 pending; 0 errors | 5 files; 0 pages; 0 pending; 0 errors | none |
| 122 | OpenStreetMap / Overpass industrial facilities | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 0 pages; 1 pending; 1 errors | public_http_502 |
| 123 | Global Energy Monitor asset and ownership API | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 124 | European Environment Agency industrial facilities | 0 files; 0 pages; 4 pending; 4 errors | 4 files; 0 pages; 0 pending; 0 errors | ConnectTimeout |
| 126 | Brazil ABVE electric vehicle registrations | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 14 pages; 0 pending; 0 errors | none |
| 127 | Brazil SENATRAN vehicle fleet | 8 files; 4 pages; 386 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 128 | IEA Global EV Data Explorer and Outlook | 0 files; 12 pages; 564 pending; 0 errors | 0 files; 1229 pages; 3771 pending; 3771 errors | public_rendered_page_too_large, scrape_gateway_http_400, scrape_gateway_http_429, scrape_incomplete_response |
| 129 | FAOSTAT food balances | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 136 | Y Combinator company directory and cohorts | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 137 | Techstars portfolio and cohorts | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 138 | 500 Global portfolio and cohorts | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 139 | Antler early-stage portfolio | 0 files; 2 pages; 0 pending; 0 errors | 0 files; 2 pages; 0 pending; 0 errors | none |
| 141 | Wefunder and Republic crowdfunding campaigns | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 144 | OpenAIRE Graph projects and research products | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 146 | Open Science Framework projects and preregistrations | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 148 | Semantic Scholar citation context | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 0 pages; 1 pending; 1 errors | public_http_429 |
| 149 | France theses.fr doctoral theses | 0 files; 11 pages; 15 pending; 1 errors | 0 files; 32 pages; 1 pending; 1 errors | scrape_gateway_http_429, scrape_incomplete_response |
| 150 | Brazil CAPES theses and dissertations | 4 files; 1 pages; 0 pending; 0 errors | 9 files; 2 pages; 0 pending; 0 errors | none |
| 152 | European Commission CORDIS | 2 files; 0 pages; 0 pending; 0 errors | 2 files; 0 pages; 0 pending; 0 errors | none |
| 154 | Brazil FAPESP PIPE and grants | 0 files; 12 pages; 23 pending; 0 errors | 0 files; 52 pages; 0 pending; 0 errors | none |
| 155 | UKRI Gateway to Research | 4 files; 0 pages; 0 pending; 0 errors | 4 files; 0 pages; 0 pending; 0 errors | none |
| 158 | University technology-transfer catalogs and reports | 10 files; 1 pages; 16 pending; 1 errors | 25 files; 1 pages; 1 pending; 1 errors | public_http_404 |
| 78 | UCDP organized violence | 3 files; 1 pages; 0 pending; 0 errors | 3 files; 1 pages; 0 pending; 0 errors | none |
| 162 | Wikimedia per-article pageviews | waiting for first attempt | waiting for first attempt | none |
| 169 | Hacker News public stories and comments | waiting for first attempt | waiting for first attempt | none |
| 170 | NIST National Vulnerability Database (CVE/CPE) | waiting for first attempt | waiting for first attempt | none |
| 176 | France BODACC commercial notices | waiting for first attempt | waiting for first attempt | none |
| 178 | Brazil CVM corporate financial filings: DFP and ITR | waiting for first attempt | waiting for first attempt | none |
| 187 | South African Competition Tribunal decided cases | waiting for first attempt | waiting for first attempt | none |
| 190 | India SEBI enforcement orders and proceedings | waiting for first attempt | waiting for first attempt | none |
| 204 | CFTC Commitments of Traders (COT) | waiting for first attempt | waiting for first attempt | none |
| 205 | FDIC BankFind financials and Summary of Deposits | waiting for first attempt | waiting for first attempt | none |
| 207 | UK DfT/DVLA vehicle licensing by make and model | waiting for first attempt | waiting for first attempt | none |
| 229 | npm package download counts and release metadata | waiting for first attempt | waiting for first attempt | none |
| 238 | CDC NHANES public-use survey/examination/laboratory data | waiting for first attempt | waiting for first attempt | none |
| 240 | CDC/NCI U.S. Cancer Statistics and NCI SEER | waiting for first attempt | waiting for first attempt | none |
| 241 | CDC ACIP recommendations and MMWR policy archive | waiting for first attempt | waiting for first attempt | none |
| 242 | WHO Global Health Observatory and disease-program downloads | waiting for first attempt | waiting for first attempt | none |
| 249 | US SEC Forms 3, 4 and 5 insider holdings and transactions | waiting for first attempt | waiting for first attempt | none |
| 264 | EIA Form EIA-923 plant generation, fuel receipts, consumption and stocks | waiting for first attempt | waiting for first attempt | none |
| 268 | Japan Robot Association (JARA) public quarterly and annual industrial-robot statistics | waiting for first attempt | waiting for first attempt | none |
| 269 | Japan Machine Tool Builders’ Association (JMTBA) public monthly machine-tool orders | waiting for first attempt | waiting for first attempt | none |
| 270 | A3 / former RIA public North American robot-order and shipment releases | waiting for first attempt | waiting for first attempt | none |
| 163 | Statcounter Global Stats | waiting for first attempt | waiting for first attempt | none |
| 171 | IETF Internet-Drafts and RFC archive | waiting for first attempt | waiting for first attempt | none |
| 177 | Spain BOE BORME commercial-register notices | waiting for first attempt | waiting for first attempt | none |
| 182 | UK CMA cases, market investigations and merger decisions | waiting for first attempt | waiting for first attempt | none |
| 183 | US FTC cases and proceedings | waiting for first attempt | waiting for first attempt | none |
| 194 | US Census Business Formation Statistics (BFS) | waiting for first attempt | waiting for first attempt | none |
| 195 | BLS Quarterly Census of Employment and Wages (QCEW): employment and establishments | waiting for first attempt | waiting for first attempt | none |
| 198 | EPA Greenhouse Gas Reporting Program (GHGRP) | waiting for first attempt | waiting for first attempt | none |
| 201 | JODI Oil and Gas world databases | waiting for first attempt | waiting for first attempt | none |
| 210 | US Census Building Permits Survey | waiting for first attempt | waiting for first attempt | none |
| 243 | WHO FluNet and FluID | waiting for first attempt | waiting for first attempt | none |
| 265 | NRC daily power-reactor status reports | waiting for first attempt | waiting for first attempt | none |

## Structured public APIs

Daily task windows record when a snapshot was observed; `job.parameters.data_start/data_end` identify the provider event-date query. Daily queries overlap seven days; NASA allows three days of publication lag. Historical tasks start in 2016 where the provider has records. Completed tasks describe their configured query, not the entire provider. Counts include committed pages from incomplete tasks and may include overlapping queries or repeated snapshots; they are not unique-publication counts.

| # | Source | Daily on t3 | Historical on c7i |
|---|---|---|---|
| 76 | nasa_power_weather_and_solar_resource | 120 complete; 0 partial; 0 failed; 840 captured observations | 88 complete; 0 partial; 0 failed; 31,608 captured observations |
| 143 | datacite_dissertations_datasets_software_and_usage | 1 complete; 33 partial; 58 failed; 23,201 captured observations | 214 complete; 164 partial; 12 failed; 1,862,376 captured observations |
| 145 | biorxiv_medrxiv_preprints | 0 complete; 7 partial; 28 failed; 140 captured observations | 105 complete; 90 partial; 47 failed; 338,621 captured observations |
| 147 | zenodo_research_artifacts_and_usage | 0 complete; 95 partial; 128 failed; 11,025 captured observations | 1982 complete; 1756 partial; 301 failed; 1,956,362 captured observations |
| 156 | hugging_face_hub_models_and_datasets | 18 complete; 12 partial; 0 failed; 439,471 captured observations | 1 complete; 0 partial; 1 failed; 1,101,139 captured observations |
| 74 | epo_ops_patent_legal_events | 1357 complete; 520 partial; 23 failed; 2,255 captured observations | 4761 complete; 1189 partial; 2 failed; 125,564 captured observations |
| 51 | un_comtrade | 908 complete; 0 partial; 0 failed; 429 captured observations | 660 complete; 0 partial; 0 failed; 562 captured observations |
| 70 | ember_electricity_demand_and_generation | 1050 complete; 0 partial; 0 failed; 738,839 captured observations | 260 complete; 0 partial; 0 failed; 167,484 captured observations |
| 71 | wto_timeseries_api | 735 complete; 258 partial; 22 failed; 524,245 captured observations | 170 complete; 61 partial; 21 failed; 252,547 captured observations |
| 72 | wto_quantitative_restrictions_api | 60 complete; 0 partial; 0 failed; 3,430 captured observations | 22 complete; 0 partial; 0 failed; 1,834 captured observations |
| 73 | wto_eping_sps_tbt_notifications | 17 complete; 0 partial; 0 failed; 5,485 captured observations | 130 complete; 0 partial; 0 failed; 60,736 captured observations |
| 75 | copernicus_era5_era5_land | 357 complete; 0 partial; 31 failed; 357 captured observations | 30 complete; 2047 partial; 3 failed; 30 captured observations |
| 118 | us_census_international_trade_api | 638 complete; 0 partial; 1647 failed; 63,110 captured observations | 1290 complete; 10 partial; 0 failed; 119,041 captured observations |
| 125 | usda_fas_production_supply_and_distribution | 150 complete; 0 partial; 0 failed; 234,030 captured observations | 55 complete; 0 partial; 0 failed; 86,261 captured observations |
| 92 | cninfo_mainland_china_company_disclosures | 0 complete; 10 partial; 0 failed; 2,695 captured observations | 0 complete; 130 partial; 0 failed; 4,508 captured observations |

USGS and NSF daily capture share the historical collectors’ request budgets and defer when those budgets are exhausted. arXiv daily capture shares the cross-host single-connection lock and four-second pacing. These daily captures retain raw responses and source records in S3 under `research-data/constellation-backfill/daily-raw/`; no Athena publication of these new daily records is claimed here.

## Athena artifact inventory

The following live table contains verified artifact metadata for the archive/document routes. It distinguishes `discovery_page` from `public_document`. It does **not** parse binary files into analytical rows. The raw files are linked by `artifact_uri`. The earlier source-status audit remains at [data-source-status-2026-10-26.md](data-source-status-2026-10-26.md).

```sql
SELECT catalog_entry, source, mode, artifact_kind, retrieved_at,
       artifact_uri, bytes, sha256, scope_note
FROM optima_regulatory_pilot.constellation_public_artifacts
WHERE source = 'sia_wsts_public_semiconductor_sales'
ORDER BY retrieved_at DESC;
```

Use the source key below for another source. Structured API records use native collection manifests and await verified publication; this inventory is not their analytical table.

| # | Source key | Selected scope |
|---|---|---|
| 1 | `gleif_legal_entities` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 4 | `hkex_prices` | HKEX public Main Board Daily Quotations with prices and volume. Public archive reach is bounded by HKEX retention. |
| 7 | `hkex_news` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 16 | `ema_ctis` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 23 | `chictr` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 24 | `nmpa_trials` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 27 | `europe_pmc_fulltext` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 28 | `crossref_proceedings` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 30 | `cms_coverage_documents` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 31 | `cms_payments_catalog` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 45 | `nist_robotics_methods` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 49 | `trade_screening` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 52 | `doe_storage_program` | Storage program main content and linked official DOE/laboratory originals; site navigation, unrelated DOE administration and exhaustive historical coverage excluded. |
| 54 | `eia_generator_index` | EIA Form 860 annual generator archive from 2016. Verify the year-specific generator workbook inside the provider ZIP. |
| 58 | `ror_institutions` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 65 | `bis_sdmx_api` | BIS central-bank policy-rate daily CSV from 2016; selected dataflow only. |
| 67 | `unido_iip_and_indstat` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 68 | `ilostat_labor_statistics` | ILOSTAT annual unemployment-by-sex/age RDS snapshot. Original vintages and forecast/observation separation are not yet extracted. |
| 69 | `imf_portwatch_shipping_activity` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 80 | `england_nhsbsa_prescribing_data` | Catalogue-only public route replaced by native NHSBSA datastore daily and historical collectors; original receipts retained. |
| 82 | `sia_wsts_public_semiconductor_sales` | WSTS public regional monthly semiconductor billings workbook; detailed paid products are excluded. |
| 83 | `semi_worldwide_equipment_billings` | SEMI/SEAJ joint worldwide semiconductor equipment billings releases and public back-number PDFs, discovered from the worldwide SEMS rows of the official co-publisher index. Japan-only and FPD rows excluded; paid full database excluded. |
| 84 | `international_federation_of_robotics_world_robotics` | Public World Robotics executive summaries and linked public reports; raw PDFs, no paid full database and no verified current market estimates inferred. |
| 85 | `iea_pvps_solar_deployment_reports` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 86 | `germany_g_ba_drug_benefit_assessments` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 87 | `france_has_medicine_assessment_opinions` | Complete official HAS medicine-evaluation exports (SMR/ASMR and links) and linked original opinions; current release, analytical interpretation and full historical archive not asserted. |
| 88 | `nice_technology_appraisals` | NICE direct licensing clarification: AI use must use licensed syndication API after cybersecurity review; development documents excluded. |
| 89 | `canada_cda_amc_cadth_reimbursement_reviews` | Complete public reimbursement review, recommendation and submitted input PDFs; document role retained, no inference of recommendation from patient/clinician input. |
| 90 | `france_assurance_maladie_open_medic` | Native annual Open Medic complete-base ZIP files and published dataset index; latest release currently 2025; all-regime medicine reimbursement aggregates, not patient records. |
| 91 | `japan_mhlw_ndb_open_data` | Native published NDB aggregate workbooks and archives; suppressed cells retained. Not individual patient data or complete fiscal-year coverage. |
| 92 | `cninfo_mainland_china_company_disclosures` | Discovery-only web route replaced by native CNINFO announcement index plus original PDF capture. Old receipts retained. |
| 93 | `china_nbs_industrial_production` | Official statistical HTML releases and original same-release figures; numerical text retained, formal series extraction and complete history not asserted. |
| 94 | `china_miit_electronics_and_battery_statistics` | Official statistical HTML releases and original same-release figures; numerical text retained, formal series extraction and complete history not asserted. |
| 95 | `china_nea_power_statistics` | Official statistical HTML releases and original same-release figures; numerical text retained, formal series extraction and complete history not asserted. |
| 96 | `china_nhsa_reimbursement_and_procurement` | Original official notices and linked public documents; no clinical interpretation, current legal-effect conclusion or confidential reimbursement values inferred. |
| 97 | `china_mofcom_export_controls` | Original official notices and linked public documents; no clinical interpretation, current legal-effect conclusion or confidential reimbursement values inferred. |
| 100 | `taiwan_twse_mops_issuer_and_revenue_archives` | Entire original TWSE issuer and monthly revenue rows; native units and reporting month retained. Current snapshots, not a complete MOPS filing archive or original historical vintages. |
| 101 | `taiwan_customs_trade_statistics` | Entire native monthly customs-clearance aggregate rows, with original reporting year and NTD-thousand units. Not detailed HS/country trade or original vintages. |
| 102 | `india_ibm_mineral_production` | Entire source-scoped native dataset/report/release with checksums; no complete historical coverage or unperformed numerical extraction asserted. |
| 103 | `indonesia_esdm_and_geological_agency_mineral_statistics` | Official mineral/coal resource-and-reserve report PDFs, including their stated data cutoff; not unrelated energy-site images or complete historical vintages. |
| 104 | `brazil_anm_mineral_yearbook` | Complete native AMB production CSV files and original yearbook PDFs; annual declared data and provider revisions, not original historical vintages. |
| 105 | `brazil_anm_cfem_mining_royalties` | Complete native CFEM revenue CSV chunks, with original payment-period fields and encoding. Revenue collections; distribution/enforcement datasets and original historical vintages not inferred. |
| 106 | `brazil_mdic_comex_stat_api` | Brazil monthly import and export totals for four fixed NCM products. Original FOB USD and net kilograms. Historical windows from 2016. |
| 107 | `chile_cochilco_production_and_mining_economics` | Official copper and other mining economics workbooks and annual reports. The current workbook covers 2000–2025. |
| 108 | `chile_sernageomin_mining_yearbooks` | Official Chilean mining yearbooks, as whole PDF files. Checks daily for archive changes. |
| 109 | `chile_sma_snifa_environmental_compliance` | The official historical sanctioning-proceedings CSV linked by SNIFA. Inspection, final sanction and regulated-unit exports are separate datasets. |
| 110 | `peru_minem_mining_bulletins_and_yearbooks` | Official mining bulletins, yearbooks and statistical annexes collected as original files. |
| 111 | `argentina_siacam_mining_indicators` | Official mining industrial production index series, changes and lithium production CSV exports. |
| 112 | `brazil_anm_sigmine_and_cadastro_mineiro` | Current SIGMINE state shapefiles and Cadastro Mineiro public CSVs. Historical dates in records represent concession events. |
| 113 | `peru_ingemmet_geocatmin` | Bounded Tacna concession snapshot. Eight native cadastral features with their returned attributes and geometry. |
| 119 | `eurostat_comext_goods_trade` | German imports and exports with the US in four mineral and battery HS6 groups. Native DS-045409 euro values and returned flags. Monthly refresh and annual series since 2016. |
| 120 | `climate_trace_industrial_assets_and_activity` | Five fixed iron-and-steel assets selected from the official 2025 ranking. Annual emissions and activity estimates since 2021 where available. |
| 122 | `openstreetmap_overpass_industrial_facilities` | Named industrial facilities in a Phoenix reference bounding box, current OSM snapshot only; not global coverage or reconstructed 2016 facilities. |
| 123 | `global_energy_monitor_asset_and_ownership_api` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 124 | `european_environment_agency_industrial_facilities` | Current IED SiteMap response with eight native point features. The site map is a current snapshot. Dated reporting coverage needs a separate archive route. |
| 126 | `brazil_abve_electric_vehicle_registrations` | ABVE’s original historical table of Brazil EV registrations from 2012 through September 2021. Full report capture. Current monthly releases require a separate route. |
| 127 | `brazil_senatran_vehicle_fleet` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 128 | `iea_global_ev_data_explorer_and_outlook` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 129 | `faostat_food_balances` | FAOSTAT normalized Food Balance Sheets bulk ZIP; year filtering and table extraction pending. |
| 136 | `y_combinator_company_directory_and_cohorts` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 137 | `techstars_portfolio_and_cohorts` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 138 | `500_global_portfolio_and_cohorts` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 139 | `antler_early_stage_portfolio` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 141 | `wefunder_and_republic_crowdfunding_campaigns` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 144 | `openaire_graph_projects_and_research_products` | Public OpenAIRE project metadata sample. This capture does not yet paginate the full graph or assert historical completeness. |
| 146 | `open_science_framework_projects_and_preregistrations` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 148 | `semantic_scholar_citation_context` | Public Semantic Scholar robotics keyword metadata sample, at most the first public result page. Full citation-context coverage needs a dedicated adapter and potentially a key. |
| 149 | `france_theses_fr_doctoral_theses` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 150 | `brazil_capes_theses_and_dissertations` | CAPES native annual theses and dissertations CSVs. Historical capture starts with the 2016 reference-year resource. |
| 152 | `european_commission_cordis` | CORDIS H2020 and Horizon Europe public project CSV archives; pre-programme coverage is not asserted. |
| 154 | `brazil_fapesp_pipe_and_grants` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 155 | `ukri_gateway_to_research` | Official GtR v3 awards result for the water query. Includes 20 native grant summaries with identifiers, dates and award values. Pagination and full historical coverage remain open. |
| 158 | `university_technology_transfer_catalogs_and_reports` | Initial Stanford and MIT public technology-transfer report indexes only; broader universities require additional configured publisher URLs. |
| 78 | `ucdp_organized_violence` | Native GED annual global and monthly candidate event exports; complete original files, current dataset versions; API token route and historical vintages remain separate. |
| 162 | `market_source_162` | Evidence-gated provider capture from the market workbook. |
| 169 | `market_source_169` | Evidence-gated provider capture from the market workbook. |
| 170 | `market_source_170` | Evidence-gated provider capture from the market workbook. |
| 176 | `market_source_176` | Evidence-gated provider capture from the market workbook. |
| 178 | `market_source_178` | Evidence-gated provider capture from the market workbook. |
| 187 | `market_source_187` | Evidence-gated provider capture from the market workbook. |
| 190 | `market_source_190` | Evidence-gated provider capture from the market workbook. |
| 204 | `market_source_204` | Evidence-gated provider capture from the market workbook. |
| 205 | `market_source_205` | Evidence-gated provider capture from the market workbook. |
| 207 | `market_source_207` | Evidence-gated provider capture from the market workbook. |
| 229 | `market_source_229` | Evidence-gated provider capture from the market workbook. |
| 238 | `market_source_238` | Evidence-gated provider capture from the market workbook. |
| 240 | `market_source_240` | Evidence-gated provider capture from the market workbook. |
| 241 | `market_source_241` | Evidence-gated provider capture from the market workbook. |
| 242 | `market_source_242` | Evidence-gated provider capture from the market workbook. |
| 249 | `market_source_249` | Evidence-gated provider capture from the market workbook. |
| 264 | `market_source_264` | Evidence-gated provider capture from the market workbook. |
| 268 | `market_source_268` | Evidence-gated provider capture from the market workbook. |
| 269 | `market_source_269` | Evidence-gated provider capture from the market workbook. |
| 270 | `market_source_270` | Evidence-gated provider capture from the market workbook. |
| 163 | `market_source_163` | Evidence-gated provider capture from the market workbook. |
| 171 | `market_source_171` | Evidence-gated provider capture from the market workbook. |
| 177 | `market_source_177` | Evidence-gated provider capture from the market workbook. |
| 182 | `market_source_182` | Evidence-gated provider capture from the market workbook. |
| 183 | `market_source_183` | Evidence-gated provider capture from the market workbook. |
| 194 | `market_source_194` | Evidence-gated provider capture from the market workbook. |
| 195 | `market_source_195` | Evidence-gated provider capture from the market workbook. |
| 198 | `market_source_198` | Evidence-gated provider capture from the market workbook. |
| 201 | `market_source_201` | Evidence-gated provider capture from the market workbook. |
| 210 | `market_source_210` | Evidence-gated provider capture from the market workbook. |
| 243 | `market_source_243` | Evidence-gated provider capture from the market workbook. |
| 265 | `market_source_265` | Evidence-gated provider capture from the market workbook. |

## Remaining work and access boundaries

API-key, approval and commercial-only sources remain on their existing access gates. Decodo is an access layer and cannot supply a missing publisher subscription. Reddit, Bluesky, GitHub SDK and Marketaux retain their existing pauses. Internal derived routes depend on their upstream data; they are not additional external publishers.

Full date coverage and source-specific parsing/pagination are still required for discovery-only routes, metadata samples, large files rejected by the size limit and archives beyond the bounded crawl. A 2016 target alone never makes those intervals complete. All attempted errors are recorded; only verified dated gaps longer than five days qualify for the existing gap action flag. Unknown date coverage is recorded as unaudited.
