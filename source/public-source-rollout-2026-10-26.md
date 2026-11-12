# Public-source collection rollout

Updated **2026-11-12 14:06:58 CET**. This file refreshes every five minutes from S3 evidence.

**Collection controls:** historical enabled; daily capture enabled on t3.

**Placement:** daily capture on t3; historical worker m7i.large. 15 configured workers share a 2-CPU / 6-GiB cap.

**Configured:** 73 public archive/document routes, 14 structured API collectors, and daily capture for the three already-running raw historical sources (USGS, NSF and arXiv). EPO OPS uses its stored credentials; the other new structured API routes are public. Paused archive rows remain visible as retained evidence; Decodo uses the existing credential.

**Observed:** 73/73 archive sources attempted by daily capture; 73/73 attempted by historical retrieval. 62 have saved at least one artifact; 35 have downloaded at least one non-HTML file. Errors below remain incomplete and retryable.

**Scope:** archive pages are discovery evidence. Downloaded files are raw captures. Neither establishes a complete structured dataset, coverage since 2016, original historical vintages, or Athena access to the file contents. Report summaries are distinct from licensed full products. API documentation/catalog captures are labelled metadata/discovery until a dataset adapter or resource downloader is implemented.

## Public archives and downloads

| # | Source | Daily on t3 | Historical on c7i | Current error codes |
|---|---|---|---|---|
| 1 | GLEIF legal entities | 0 files; 12 pages; 118 pending; 0 errors | 610 files; 678 pages; 81 pending; 81 errors | public_http_404, unreviewed_public_redirect |
| 4 | HKEX prices | 0 files; 11 pages; 159 pending; 1 errors | 630 files; 975 pages; 14 pending; 14 errors | public_http_404, public_redirect_limit, unreviewed_public_redirect |
| 7 | HKEX announcements | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 16 | EMA Clinical Trials Information System | 0 files; 12 pages; 41 pending; 0 errors | 0 files; 53 pages; 0 pending; 0 errors | none |
| 23 | Chinese Clinical Trial Registry | 0 files; 1 pages; 19 pending; 11 errors | 0 files; 1 pages; 19 pending; 19 errors | public_http_405 |
| 24 | NMPA trials | 0 files; 1 pages; 1 pending; 1 errors | 0 files; 1 pages; 2 pending; 2 errors | public_http_202 |
| 27 | Europe PMC full text | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 17 pages; 25 pending; 25 errors | scrape_gateway_http_429, scrape_incomplete_response, scrape_target_http_404 |
| 28 | Crossref conference proceedings | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 30 | CMS coverage documents | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 31 | CMS payments catalog and financial records | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 45 | NIST robotics methods | 0 files; 11 pages; 99 pending; 1 errors | 2 files; 589 pages; 158 pending; 158 errors | public_http_405 |
| 49 | Trade screening lists | 4 files; 8 pages; 76 pending; 0 errors | 54 files; 87 pages; 0 pending; 0 errors | none |
| 52 | Department of Energy storage program | 4 files; 8 pages; 15 pending; 0 errors | 8 files; 23 pages; 1 pending; 1 errors | public_http_404 |
| 54 | EIA generator index | 11 files; 1 pages; 39 pending; 0 errors | 2701 files; 2246 pages; 53 pending; 53 errors | public_asset_too_large, public_http_404 |
| 58 | Research Organization Registry institutions | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 65 | BIS SDMX API | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 67 | UNIDO IIP and INDSTAT | 2 files; 0 pages; 0 pending; 0 errors | 2 files; 0 pages; 0 pending; 0 errors | none |
| 68 | ILOSTAT labor statistics | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 69 | IMF PortWatch shipping activity | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 80 | England NHSBSA prescribing data | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 82 | SIA / WSTS public semiconductor sales | 3 files; 4 pages; 10 pending; 5 errors | 8 files; 22 pages; 6 pending; 6 errors | unreviewed_public_redirect |
| 83 | SEMI worldwide equipment billings | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 0 pages; 1 pending; 1 errors | scrape_gateway_http_429, scrape_incomplete_response |
| 84 | International Federation of Robotics World Robotics | 11 files; 1 pages; 168 pending; 0 errors | 181 files; 4 pages; 0 pending; 0 errors | none |
| 85 | IEA-PVPS solar deployment reports | 0 files; 12 pages; 51 pending; 0 errors | 138 files; 123 pages; 0 pending; 0 errors | none |
| 86 | Germany G-BA drug benefit assessments | 1 files; 5 pages; 0 pending; 0 errors | 1 files; 5 pages; 0 pending; 0 errors | none |
| 87 | France HAS medicine assessment opinions | 0 files; 12 pages; 198 pending; 0 errors | 0 files; 4110 pages; 0 pending; 0 errors | none |
| 88 | NICE technology appraisals | PAUSED — retained prior evidence only | PAUSED — retained prior evidence only | none |
| 89 | Canada CDA-AMC / CADTH reimbursement reviews | 0 files; 9 pages; 282 pending; 3 errors | 0 files; 1828 pages; 710 pending; 710 errors | InterfaceError, scrape_gateway_http_400, scrape_gateway_http_429, scrape_gateway_http_500, scrape_incomplete_response, scrape_target_http_404 |
| 90 | France Assurance Maladie Open Medic | 0 files; 2 pages; 46 pending; 10 errors | 12 files; 3061 pages; 1927 pending; 370 errors | public_http_404, public_http_410, public_http_502, unreviewed_public_redirect |
| 91 | Japan MHLW NDB Open Data | 3 files; 9 pages; 183 pending; 0 errors | 3 files; 193 pages; 0 pending; 0 errors | none |
| 92 | CNINFO mainland-China company disclosures | 0 files; 12 pages; 15 pending; 0 errors | 0 files; 18 pages; 9 pending; 9 errors | unreviewed_public_redirect |
| 93 | China NBS industrial production | 0 files; 10 pages; 7 pending; 2 errors | 0 files; 16 pages; 1 pending; 1 errors | public_http_404, scrape_gateway_http_400 |
| 94 | China MIIT electronics and battery statistics | 0 files; 12 pages; 72 pending; 0 errors | 4 files; 78 pages; 0 pending; 0 errors | none |
| 95 | China NEA power statistics | 0 files; 12 pages; 65 pending; 0 errors | 15 files; 66 pages; 0 pending; 0 errors | none |
| 96 | China NHSA reimbursement and procurement | 0 files; 10 pages; 113 pending; 2 errors | 37 files; 143 pages; 0 pending; 0 errors | scrape_gateway_http_400 |
| 97 | China MOFCOM export controls | 0 files; 12 pages; 30 pending; 0 errors | 19 files; 34 pages; 0 pending; 0 errors | none |
| 100 | Taiwan TWSE/MOPS issuer and revenue archives | 2 files; 0 pages; 0 pending; 0 errors | 2 files; 0 pages; 0 pending; 0 errors | none |
| 101 | Taiwan customs trade statistics | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 0 pages; 1 pending; 1 errors | scrape_gateway_http_400, scrape_gateway_http_429 |
| 102 | India IBM mineral production | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 0 pages; 1 pending; 1 errors | unreviewed_public_redirect |
| 103 | Indonesia ESDM and Geological Agency mineral statistics | 11 files; 1 pages; 6 pending; 0 errors | 26 files; 17 pages; 2 pending; 2 errors | public_asset_too_large |
| 104 | Brazil ANM mineral yearbook | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 0 pages; 1 pending; 1 errors | public_http_404 |
| 105 | Brazil ANM CFEM mining royalties | 7 files; 1 pages; 15 pending; 4 errors | 10 files; 2 pages; 10 pending; 10 errors | public_http_404 |
| 106 | Brazil MDIC Comex Stat API | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 0 pages; 1 pending; 1 errors | public_http_401 |
| 107 | Chile COCHILCO production and mining economics | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 0 pages; 1 pending; 1 errors | unreviewed_public_redirect |
| 108 | Chile SERNAGEOMIN mining yearbooks | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 0 pages; 1 pending; 1 errors | scrape_gateway_http_429, scrape_target_http_404 |
| 109 | Chile SMA SNIFA environmental compliance | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 110 | Peru MINEM mining bulletins and yearbooks | 0 files; 11 pages; 36 pending; 1 errors | 0 files; 133 pages; 1 pending; 1 errors | unreviewed_public_redirect |
| 111 | Argentina SIACAM mining indicators | 1 files; 1 pages; 0 pending; 0 errors | 1 files; 1 pages; 0 pending; 0 errors | none |
| 112 | Brazil ANM SIGMINE and Cadastro Mineiro | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 1 pages; 0 pending; 0 errors | scrape_gateway_http_429 |
| 113 | Peru INGEMMET GEOCATMIN | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 0 pages; 1 pending; 1 errors | scrape_gateway_http_400, scrape_gateway_http_429 |
| 119 | Eurostat Comext goods trade | 0 files; 12 pages; 110 pending; 0 errors | 387 files; 1796 pages; 18 pending; 18 errors | public_asset_too_large, public_http_404, unreviewed_public_redirect |
| 120 | Climate TRACE industrial assets and activity | 0 files; 4 pages; 0 pending; 0 errors | 0 files; 4 pages; 0 pending; 0 errors | none |
| 122 | OpenStreetMap / Overpass industrial facilities | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 0 pages; 1 pending; 1 errors | ReadTimeout, public_http_502 |
| 123 | Global Energy Monitor asset and ownership API | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 124 | European Environment Agency industrial facilities | 0 files; 11 pages; 2 pending; 1 errors | 1 files; 11 pages; 1 pending; 1 errors | public_http_410 |
| 126 | Brazil ABVE electric vehicle registrations | 0 files; 12 pages; 3 pending; 0 errors | 0 files; 12 pages; 0 pending; 0 errors | none |
| 127 | Brazil SENATRAN vehicle fleet | 8 files; 4 pages; 386 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 128 | IEA Global EV Data Explorer and Outlook | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 1174 pages; 3826 pending; 3826 errors | public_rendered_page_too_large, scrape_gateway_http_400, scrape_gateway_http_429, scrape_gateway_http_502, scrape_incomplete_response, scrape_target_http_10001, scrape_target_http_404 |
| 129 | FAOSTAT food balances | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 136 | Y Combinator company directory and cohorts | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 137 | Techstars portfolio and cohorts | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 138 | 500 Global portfolio and cohorts | 0 files; 1 pages; 0 pending; 0 errors | 0 files; 1 pages; 0 pending; 0 errors | none |
| 139 | Antler early-stage portfolio | 0 files; 2 pages; 0 pending; 0 errors | 0 files; 2 pages; 0 pending; 0 errors | none |
| 141 | Wefunder and Republic crowdfunding campaigns | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 1 pages; 0 pending; 0 errors | scrape_gateway_http_429 |
| 144 | OpenAIRE Graph projects and research products | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 146 | Open Science Framework projects and preregistrations | 1 files; 0 pages; 0 pending; 0 errors | 1 files; 0 pages; 0 pending; 0 errors | none |
| 148 | Semantic Scholar citation context | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 0 pages; 1 pending; 1 errors | public_http_429 |
| 149 | France theses.fr doctoral theses | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 32 pages; 1 pending; 1 errors | scrape_gateway_http_429, scrape_incomplete_response |
| 150 | Brazil CAPES theses and dissertations | 0 files; 0 pages; 1 pending; 1 errors | 285 files; 500 pages; 32 pending; 32 errors | public_asset_too_large, scrape_gateway_http_400, scrape_gateway_http_429 |
| 152 | European Commission CORDIS | 2 files; 0 pages; 0 pending; 0 errors | 2 files; 0 pages; 0 pending; 0 errors | none |
| 154 | Brazil FAPESP PIPE and grants | 0 files; 12 pages; 24 pending; 0 errors | 0 files; 52 pages; 0 pending; 0 errors | none |
| 155 | UKRI Gateway to Research | 0 files; 0 pages; 1 pending; 1 errors | 0 files; 0 pages; 1 pending; 1 errors | public_http_400 |
| 158 | University technology-transfer catalogs and reports | 10 files; 1 pages; 16 pending; 1 errors | 25 files; 1 pages; 1 pending; 1 errors | public_http_404 |

## Structured public APIs

Daily task windows record when a snapshot was observed; `job.parameters.data_start/data_end` identify the provider event-date query. Daily queries overlap seven days; NASA allows three days of publication lag. Historical tasks start in 2016 where the provider has records. Completed tasks describe their configured query, not the entire provider. Counts include committed pages from incomplete tasks and may include overlapping queries or repeated snapshots; they are not unique-publication counts.

| # | Source | Daily on t3 | Historical on c7i |
|---|---|---|---|
| 76 | nasa_power_weather_and_solar_resource | 120 complete; 0 partial; 0 failed; 840 captured observations | 88 complete; 0 partial; 0 failed; 31,608 captured observations |
| 143 | datacite_dissertations_datasets_software_and_usage | 16 complete; 4 partial; 44 failed; 68,877 captured observations | 111 complete; 218 partial; 61 failed; 955,614 captured observations |
| 145 | biorxiv_medrxiv_preprints | 4 complete; 2 partial; 15 failed; 4,430 captured observations | 105 complete; 90 partial; 66 failed; 340,311 captured observations |
| 147 | zenodo_research_artifacts_and_usage | 0 complete; 61 partial; 67 failed; 6,450 captured observations | 750 complete; 3168 partial; 121 failed; 872,325 captured observations |
| 156 | hugging_face_hub_models_and_datasets | 28 complete; 2 partial; 0 failed; 537,183 captured observations | 1 complete; 1 partial; 0 failed; 2,683,139 captured observations |
| 74 | epo_ops_patent_legal_events | 2323 complete; 402 partial; 7 failed; 1,518 captured observations | 2344 complete; 774 partial; 6 failed; 34,696 captured observations |
| 51 | un_comtrade | 977 complete; 0 partial; 1 failed; 467 captured observations | 660 complete; 0 partial; 0 failed; 562 captured observations |
| 70 | ember_electricity_demand_and_generation | 1042 complete; 0 partial; 0 failed; 723,817 captured observations | 260 complete; 0 partial; 0 failed; 167,484 captured observations |
| 71 | wto_timeseries_api | 758 complete; 123 partial; 16 failed; 317,141 captured observations | 64 complete; 21 partial; 9 failed; 90,250 captured observations |
| 72 | wto_quantitative_restrictions_api | 60 complete; 0 partial; 0 failed; 3,413 captured observations | 22 complete; 0 partial; 0 failed; 1,834 captured observations |
| 73 | wto_eping_sps_tbt_notifications | 26 complete; 0 partial; 0 failed; 4,028 captured observations | 130 complete; 0 partial; 0 failed; 60,736 captured observations |
| 75 | copernicus_era5_era5_land | 176 complete; 0 partial; 23 failed; 176 captured observations | 0 complete; 1492 partial; 5 failed; 0 captured observations |
| 118 | us_census_international_trade_api | 355 complete; 0 partial; 1587 failed; 24,225 captured observations | 646 complete; 0 partial; 173 failed; 59,621 captured observations |
| 125 | usda_fas_production_supply_and_distribution | 60 complete; 0 partial; 0 failed; 95,141 captured observations | 55 complete; 0 partial; 0 failed; 86,261 captured observations |

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
| 4 | `hkex_prices` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
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
| 52 | `doe_storage_program` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 54 | `eia_generator_index` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 58 | `ror_institutions` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 65 | `bis_sdmx_api` | BIS central-bank policy-rate daily CSV from 2016; selected dataflow only. |
| 67 | `unido_iip_and_indstat` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 68 | `ilostat_labor_statistics` | ILOSTAT annual unemployment-by-sex/age RDS snapshot. Original vintages and forecast/observation separation are not yet extracted. |
| 69 | `imf_portwatch_shipping_activity` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 80 | `england_nhsbsa_prescribing_data` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 82 | `sia_wsts_public_semiconductor_sales` | WSTS public regional monthly semiconductor billings workbook; detailed paid products are excluded. |
| 83 | `semi_worldwide_equipment_billings` | Public press releases and report summaries only; licensed full historical datasets are excluded. |
| 84 | `international_federation_of_robotics_world_robotics` | Public press releases and report summaries only; licensed full historical datasets are excluded. |
| 85 | `iea_pvps_solar_deployment_reports` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 86 | `germany_g_ba_drug_benefit_assessments` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 87 | `france_has_medicine_assessment_opinions` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 88 | `nice_technology_appraisals` | NICE direct licensing clarification: AI use must use licensed syndication API after cybersecurity review; development documents excluded. |
| 89 | `canada_cda_amc_cadth_reimbursement_reviews` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 90 | `france_assurance_maladie_open_medic` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 91 | `japan_mhlw_ndb_open_data` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 92 | `cninfo_mainland_china_company_disclosures` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 93 | `china_nbs_industrial_production` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 94 | `china_miit_electronics_and_battery_statistics` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 95 | `china_nea_power_statistics` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 96 | `china_nhsa_reimbursement_and_procurement` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 97 | `china_mofcom_export_controls` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 100 | `taiwan_twse_mops_issuer_and_revenue_archives` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 101 | `taiwan_customs_trade_statistics` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 102 | `india_ibm_mineral_production` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 103 | `indonesia_esdm_and_geological_agency_mineral_statistics` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 104 | `brazil_anm_mineral_yearbook` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 105 | `brazil_anm_cfem_mining_royalties` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 106 | `brazil_mdic_comex_stat_api` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 107 | `chile_cochilco_production_and_mining_economics` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 108 | `chile_sernageomin_mining_yearbooks` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 109 | `chile_sma_snifa_environmental_compliance` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 110 | `peru_minem_mining_bulletins_and_yearbooks` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 111 | `argentina_siacam_mining_indicators` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 112 | `brazil_anm_sigmine_and_cadastro_mineiro` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 113 | `peru_ingemmet_geocatmin` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 119 | `eurostat_comext_goods_trade` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 120 | `climate_trace_industrial_assets_and_activity` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 122 | `openstreetmap_overpass_industrial_facilities` | Named industrial facilities in a Phoenix reference bounding box, current OSM snapshot only; not global coverage or reconstructed 2016 facilities. |
| 123 | `global_energy_monitor_asset_and_ownership_api` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 124 | `european_environment_agency_industrial_facilities` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 126 | `brazil_abve_electric_vehicle_registrations` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
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
| 150 | `brazil_capes_theses_and_dissertations` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 152 | `european_commission_cordis` | CORDIS H2020 and Horizon Europe public project CSV archives; pre-programme coverage is not asserted. |
| 154 | `brazil_fapesp_pipe_and_grants` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 155 | `ukri_gateway_to_research` | Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. |
| 158 | `university_technology_transfer_catalogs_and_reports` | Initial Stanford and MIT public technology-transfer report indexes only; broader universities require additional configured publisher URLs. |

## Remaining work and access boundaries

API-key, approval and commercial-only sources remain on their existing access gates. Decodo is an access layer and cannot supply a missing publisher subscription. Reddit, Bluesky, GitHub SDK and Marketaux retain their existing pauses. Internal derived routes depend on their upstream data; they are not additional external publishers.

Full date coverage and source-specific parsing/pagination are still required for discovery-only routes, metadata samples, large files rejected by the size limit and archives beyond the bounded crawl. A 2016 target alone never makes those intervals complete. All attempted errors are recorded; only verified dated gaps longer than five days qualify for the existing gap action flag. Unknown date coverage is recorded as unaudited.
