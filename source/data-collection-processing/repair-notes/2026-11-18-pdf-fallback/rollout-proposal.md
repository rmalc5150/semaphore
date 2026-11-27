# Proposed activation for the remaining PDF collectors

The owner requested an expensive residential proxy only after other PDF routes fail. The preprint route has been validated and can be activated separately. Automatic approval review rejected a combined production-cache seed and deployment across every daily workspace as too broad. This narrower proposal seeds no production cache and limits further activation to named PDF collectors.

## Exact scope

Retain `biorxiv_medrxiv_preprints`; add these source keys to the activation allowlist:

- `hkex_news`
- `disclosure_documents`
- `usgs_minerals`
- `nist_robotics_methods`
- `europe_pmc_fulltext`
- `uk_mhra`
- `japan_pmda`
- `canada_cda_amc_cadth_reimbursement_reviews`
- `france_has_medicine_assessment_opinions`
- `germany_g_ba_drug_benefit_assessments`
- `iea_pvps_solar_deployment_reports`

Activation targets are the shared auxiliary/capture runtimes and existing isolated historical/daily workspaces for those source keys only. Preserve worker-specific source code, unrelated configuration, existing operator pauses and raw-validation holds. The paid route applies only to public HTTPS URLs identifiable as PDFs; authenticated requests, credential-bearing/signed URLs and extensionless downloads are outside this implementation.

## Fixed shared safeguards

- Existing downloader, then a normal HTTPS retry, before paid proxy.
- Validated cache reused for 24 hours; checksum and strict PDF checks repeated.
- **Four paid requests per UTC day across all sources and both hosts combined.**
- **8 MiB maximum PDF body; 32 MiB conservatively reserved per day**, plus network/protocol overhead.
- One paid attempt per URL per day and one per collector-client invocation. Failures count; no automatic paid retry or paid redirect chain.
- No paid requests for missing files, authentication errors, rate limits or known oversized files.
- Strict PDF validation and preprint DOI validation before storing successful proxy downloads.
- No source API keys/cookies forwarded; TLS verification remains enabled.
- No new plan, account, IAM permission, raw-data deletion or manual notification.

Two paid diagnostic downloads for the replacement password have already been counted in today's shared allowance. Worker-side cache and real shared-quota guard tests made zero paid requests.

## Risk and rollback

Enabling additional sources permits paid traffic that could consume the shared allowance without recovering useful data. Other PDF sources can therefore use up capacity a preprint might otherwise use. They cannot increase the four-request shared cap. Unknown/private URL forms are skipped rather than proxied. Set `enabled` to false or remove an individual source from `allowed_sources` to stop its paid fallback; original downloads continue.

No production-cache seed is included. Source-specific live capture and publication remain subject to their existing contracts and checks.
