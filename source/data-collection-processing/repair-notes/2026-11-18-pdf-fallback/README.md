# Last-resort PDF proxy fallback — enabled 18 November 2026

**The residential proxy is enabled as the final transport for the 12 approved public-PDF collectors.** The replacement password was verified and passed two budgeted, native-PDF download tests. Existing source pauses, raw-validation holds and source-specific publication requirements remain unchanged.

## Download order and cost controls

1. The existing ordinary downloader and its normal retry policy run first.
2. After an eligible failure, reuse a checksum/PDF-validated cache entry up to 24 hours old, if present.
3. Otherwise try a separate ordinary HTTPS download, including safely checked redirects.
4. Only after those fail, permit one residential-proxy attempt.

Shared limits across controller, worker and all approved sources:

| Control | Limit |
| --- | --- |
| Paid requests | **4 per UTC day total**, including failures |
| PDF body | **8 MiB per paid attempt** |
| Reserved daily body allowance | **32 MiB**, plus network/protocol overhead |
| Same URL | **1 paid attempt per UTC day** |
| Collector client | **1 paid attempt per invocation** |
| Paid retries / redirect chains | **None** |
| Cache | Strictly revalidated; maximum 24 hours old |

The maximum body allowance is reserved before the paid request and is not refunded after small downloads or failures. This deliberately favours cost control over throughput. Two paid downloads used to verify the replacement password count toward today's four-attempt allowance. Worker verification used no additional paid requests. Missing files, authentication errors, rate limits and known oversized files do not trigger the paid route. A budget stop leaves the affected scope incomplete and retryable; it does not stop unrelated sources or ordinary downloads.

Strict PDF parsing, checksum validation and a preprint DOI check run before a fallback artifact is saved. Source API keys/cookies are not forwarded to the proxy. TLS verification remains enabled. Credential-bearing/signed URLs, private-network targets, authenticated fetches and extensionless download routes are excluded from this implementation.

## Approved activation

The owner explicitly approved [the exact rollout proposal](rollout-proposal.md). Allowed source keys are:

`biorxiv_medrxiv_preprints`, `hkex_news`, `disclosure_documents`, `usgs_minerals`, `nist_robotics_methods`, `europe_pmc_fulltext`, `uk_mhra`, `japan_pmda`, `canada_cda_amc_cadth_reimbursement_reviews`, `france_has_medicine_assessment_opinions`, `germany_g_ba_drug_benefit_assessments`, `iea_pvps_solar_deployment_reports`.

The shared downloaders, relevant historical runtimes and matching existing daily workspace were configured. All other source workspaces remain disabled for paid PDF fallback. Worker-specific code was preserved through narrow patches and original runtime files were backed up. An over-broad runtime filename match also touched CNINFO's configuration; its source was never allowed by the guard, and its flag was restored to disabled. No new account, plan or IAM permission was introduced.

An initial combined production-cache seed/all-daily-workspace rollout was rejected by automatic approval review as too broad. That command was not executed. The subsequent scoped validation and explicitly approved expansion **seeded no production cache**. The validated PDF cache in the worker integration test was local diagnostic storage only.

## Verification

- **151 regression checks passed**, including free-download precedence, strict validation, no paid retries/redirects, byte limits, sensitive-error redaction, URL cooldown, shared transactional quota, cache reuse, non-enrolled-source exclusion, rate-limit exhaustion and preprint cursor continuity after one paid success.
- Replacement-password tests downloaded a known control and the medRxiv PDF through the proxy. Both matched direct originals byte-for-byte; medRxiv was 49 pages with the expected DOI.
- Worker integration recovered a simulated initial failure from a locally validated cache, without network or paid calls.
- The worker's real shared URL cooldown prevented a second paid request for a URL already used by the controller.
- Actual worker read access to the cache namespace and write/readback of a non-data audit receipt passed. No original data, collection checkpoint or production PDF cache was seeded for these tests.
- Activation readback showed all 12 source keys, the shared four-request cap and the 8 MiB file limit. This establishes fallback configuration/transport controls, **not full historical capture, metadata completion or Athena publication for every source**.

## Implementation and evidence

- `pdf_proxy_fallback.py`: safe transport, cache, PDF validation, shared RDS quotas and redacted receipts.
- `regulatory_collection.py`: last-resort interception of eligible ordinary public PDF downloads.
- `public_source_capture.py`: native binary fallback for reviewed public PDF routes; HTML scraping is not used to reconstruct PDFs.
- `additional_source_apis.py`: commit immediately after one paid preprint succeeds, avoiding loss/rebilling if a later paper fails.
- `config/pdf-proxy-fallback.json`: enabled flag, approved source keys and fixed caps; contains no credentials.
- `tests.log`, `rotated-proxy-results.json`, `worker-limited-validation-result.json`, `approved-expansion-result.json`, `final-worker-check-result.json`: validation/deployment evidence.
- `rotation-verified.json`: non-secret verification that the password changed.

Successful fallback PDFs use the normal `source_documents/<source>/<sha256>` contract and original provider URL. Cache and attempt receipts use `constellation-backfill/source-metadata/operations/pdf-proxy/`. Collection checkpoints/publication proceed through the existing source pipeline; paid transport does not bypass their completeness checks.

## Owner action

**None for this setup.** Password rotation and proxy access are verified; the approved fallback is enabled. Keep the current cap unless actual use justifies changing it. The old Decodo JSON/base64 PDF route remains disabled. To stop paid fallback, set `enabled` to false, or remove a source from `allowed_sources`; ordinary capture continues.
