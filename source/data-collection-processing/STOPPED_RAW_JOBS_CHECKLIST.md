# Stopped raw-data jobs checklist

Checked 4 November 2026. This covers all 87 sources with `raw_failed` metadata-engine attempts in the current inventory. Order is highest intervention required first. The exact job IDs, reasons, counts, and representative input keys are in `s3://raw-059416028963-us-east-1-an/temporary/raw-source-audit/2026-10-31/raw-error-inventory.json`.

## November 11 update for grants, procurement and patents

The configured NIH, NIST, USAspending, TED, USPTO assignment, USPTO ODP and Google Patents routes now have verified Athena records and enabled metadata processing. See [the scoped review and evidence](repair-notes/2026-11-11-grants-patents-procurement/README.md). This supersedes their older stopped-validator status. Full patent text remains a separate requirement for the bibliographic routes. One old NIH batch with no commit-checkpoint head remains explicitly uncommitted; its raw files are retained.

## Current saved evidence — S3 URLs

Use the source key beside every checkbox with the applicable URL below:

| Failure/input type | Current saved location |
| --- | --- |
| Raw collector input | `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=<SOURCE_KEY>/` |
| Public discovery/download route | `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/<SOURCE_KEY>/` |
| Exact representative saved object for **every** source | `s3://raw-059416028963-us-east-1-an/temporary/raw-source-audit/2026-10-31/raw-error-inventory.json` |

The inventory record for each source contains `example_input_key`; prepend `s3://data-collection-059416028963-us-east-1-an/` to open that precise currently saved input. This avoids pointing at a guessed object when a source has both raw and public-capture attempts.

## Priority order and common completion rule

Every item is complete only when its listed original provider artifact is saved, checksummed, type-validated, tied to the provider identity, and referenced as the required artifact kind. A successful index/API page alone is not completion.

## A. Access, licence, or entitlement decision required

These cannot be fixed by retrying the current public capture. Confirm permitted machine-readable delivery, licence/use terms, and the raw-data contract first.

- [ ] `cninfo_mainland_china_company_disclosures`
- [ ] `ember_electricity_demand_and_generation`
- [ ] `iea_global_ev_data_explorer_and_outlook`
- [ ] `international_federation_of_robotics_world_robotics`
- [ ] `sia_wsts_public_semiconductor_sales`
- [ ] `south_korea_fss_opendart`
- [ ] `un_comtrade`
- [ ] `wto_eping_sps_tbt_notifications`
- [ ] `wto_quantitative_restrictions_api`

## B. Substantive-document contract required

Define and retrieve the versioned original full text, filing, or patent document; metadata/abstract/index records are insufficient.

- [ ] `arxiv`
- [ ] `biorxiv_medrxiv_preprints`
- [ ] `brazil_capes_theses_and_dissertations`
- [x] `crossref_proceedings` — reviewed November 10 for complete original DOI/proceedings metadata; incorrect full-paper gate repaired. Publisher full papers remain a separate coverage gap. [Scope and Athena proof](repair-notes/2026-11-10-crossref/README.md).
- [ ] `datacite_dissertations_datasets_software_and_usage`
- [ ] `europe_pmc`
- [ ] `europe_pmc_fulltext`
- [ ] `google_patents_bigquery`
- [ ] `hkex_news`
- [ ] `pubmed_abstracts`
- [ ] `sec_edgar`
- [ ] `taiwan_twse_mops_issuer_and_revenue_archives`
- [ ] `uspto_odp`

## C. Public discovery page must be replaced by an actual file/export

Implement explicit official download/API-resource extraction, then verify the resulting CSV, ZIP, PDF, spreadsheet, XML, or JSON payload.

- [ ] `brazil_abve_electric_vehicle_registrations`
- [ ] `brazil_anm_sigmine_and_cadastro_mineiro`
- [ ] `brazil_fapesp_pipe_and_grants`
- [ ] `brazil_senatran_vehicle_fleet`
- [ ] `canada_cda_amc_cadth_reimbursement_reviews`
- [ ] `china_miit_electronics_and_battery_statistics`
- [ ] `china_mofcom_export_controls`
- [ ] `china_nbs_industrial_production`
- [ ] `china_nea_power_statistics`
- [ ] `china_nhsa_reimbursement_and_procurement`
- [ ] `eia_generator_index`
- [ ] `ema_ctis`
- [ ] `european_environment_agency_industrial_facilities`
- [ ] `eurostat_comext_goods_trade`
- [ ] `france_assurance_maladie_open_medic`
- [ ] `france_has_medicine_assessment_opinions`
- [ ] `france_theses_fr_doctoral_theses`
- [ ] `germany_g_ba_drug_benefit_assessments`
- [ ] `gleif_legal_entities`
- [ ] `global_energy_monitor_asset_and_ownership_api`
- [ ] `hkex_prices`
- [ ] `iea_pvps_solar_deployment_reports`
- [ ] `indonesia_esdm_and_geological_agency_mineral_statistics`
- [ ] `japan_mhlw_ndb_open_data`
- [ ] `nist_robotics_methods`
- [ ] `peru_minem_mining_bulletins_and_yearbooks`
- [ ] `university_technology_transfer_catalogs_and_reports`
- [ ] `wefunder_and_republic_crowdfunding_campaigns`

## D. Collector correctness defect

- [ ] `eodhd` — reconcile inventory payload with the provider response, then archive the unmodified response.
- [ ] `nsf_awards` — remove the field projection; retain the complete raw provider response.

## E. Raw response exists but is not attached/verified

Archive the unmodified provider response and attach it as `provider_record`; then validate checksum, MIME/content, host, and record identity.

- [ ] `canada_noc`, `chictr`, `clinicaltrials_gov`, `cpsc_recalls`
- [ ] `doe_storage_program`, `drugsfda_applications`, `ema_medicines`, `england_nhsbsa_prescribing_data`, `eodhd_market`, `epo_ops_patent_legal_events`
- [ ] `fda_dd_inspections_classifications`, `fda_openfda`, `fda_product_codes`
- [ ] `federal_register`, `federal_register_documents`, `finlight`, `hugging_face_hub_models_and_datasets`, `japan_pmda`, `mlperf_results`, `nih_reporter`, `nmpa_trials`
- [ ] `people_rss`, `personnel_archive`, `ted_notices`, `uk_mhra`, `usa_spending`, `uspto_assignment_histories`, `zenodo_research_artifacts_and_usage`

## 1. International Federation of Robotics — World Robotics

- [ ] **Do not retry the current public-capture receipt.** Job `53154256d207c6414ab4264b59863b4ce65e8080fc43ccfbd20ca52de2199011` stopped with `missing_verified_raw_artifacts:provider_record`.
- [ ] **Classify the source as licensed-data pending**, not as an API/scraping failure. The configured public route explicitly covers press releases and report summaries only; the World Robotics historical dataset is licensed.
- [ ] **Define the raw-data contract before collection:** licensed, machine-readable World Robotics export(s), with the provider's country/industry/application dimensions, annual observation period, units, revisions/vintages where supplied, data dictionary, and licence/use evidence.
- [ ] **Obtain rights and a delivery route** from IFR (licensed download, API, or approved bulk export). Record the authorised hosts, authentication method, permitted retention, and commercial/ML use terms.
- [ ] **Implement a dedicated licensed-file collector** that saves the original export and its accompanying data dictionary/licence receipt. Reject web pages, images, thumbnails, press-release summaries, and third-party reproductions.
- [ ] **Validate one bounded sample**: provider identity, MIME/type, checksum, period/dimensions, and a row-level reconciliation against the provider's stated totals.
- [ ] **Only then resume metadata labelling** with `provider_record` backed by that verified export.

## Evidence

- Failed report: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/metadata-engine/runtime-v2/jobs/53154256d207c6414ab4264b59863b4ce65e8080fc43ccfbd20ca52de2199011/attempts/4cdbdcfd-71a5-4d0e-bbb2-81ce3c94a6d0.json`
- The failed receipt points to a 190,766-byte `image/jpeg`, not data: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/public-capture/objects/international_federation_of_robotics_world_robotics/7b78cea7492b4dccaa5029909466e54c73b723627352f7f1a8f8b1bed2ec0930`
- Current collector scope: public press material only; it is expressly not a full historical dataset route.


## CMS coverage review — 10 November 2026

- [x] `cms_coverage` and `cms_coverage_documents`: source-specific original-response validation repaired, failed batches replayed, and fresh metadata/curated Athena queries passed. Both sources enabled. Review covers national NCD inventories and full API document bodies; annual/version capture and metadata/publication catchup continue. See [CMS repair evidence](repair-notes/2026-11-10-cms/README.md).


## CMS payments review — 11 November 2026

- [x] `cms_payments_catalog`: complete descriptor validation repaired; fresh catalog verified in metadata and specialist Athena tables. Actual financial rows separately verified in dedicated payment/spending tables: 76,013,225 and 63,336 rows. Restored daily refresh/publication from preserved checkpoints. [Current scope, evidence and SQL](repair-notes/2026-11-11-cms-payments/README.md).


## FDA feed review — 11 November 2026

- [x] `fda_dd_compliance_actions`, `fda_dd_import_refusals`, `fda_dd_inspections_citations`, `fda_ires_recalls`, `fda_product_codes`: source-specific original-response validation repaired; fresh records and actual fields verified in metadata and specialist Athena tables. All five enabled. Review covers configured Dashboard/recall fields and the 89-industry reference, not primary documents, a full product-code hierarchy or completed history. [Evidence and SQL](repair-notes/2026-11-11-fda-authenticated/README.md).
