> Update: the isolated repair results and remaining conditions are recorded in [the completed replay audit](../2026-10-21-individual-replays/README.md). The original blocker descriptions below are a prior diagnostic snapshot. Reddit, Bluesky and GitHub are now paused at user request.

# Collection blockers and repair guide

Evidence reviewed October 21, 2026. Health snapshot: **19:30 Madrid time**. Includes all issues in the 29-service health snapshot and failed/blocked scopes in the four specialist schedulers. These schedulers retain older failures: an entry below means its exact scope needs reconciliation, not necessarily that the provider is still failing today. This is not an exhaustive audit of every installed service or every source document.

**Your current tasks:** wait for the SMS review and optionally inspect published data in Athena. The repairs below are implementation work. No new purchase or credential replacement is established as necessary.

**Priority order:** keep daily capture current; verify repaired collectors and publication; repair persistent request/parser failures; then resolve unsupported historical coverage. Ordinary historical work is not itself a failure.

## 1. Shared worker queue and publication backlog — implementation

Status: capacity upgraded; larger publication batches deployed; sustained backlog reduction not yet demonstrated.

1. Confirm `optima-data.slice` has MemoryMax=6442450944 and heavy workers have MemoryMax=5368709120. Preserve the shared runtime lock until workers have isolated state/workspaces.
2. Compare daily capture freshness, oldest unpublished window, and newly queued versus verified publications over successive runs. Use `../2026-10-21-post-upgrade/backlog-baseline.json` as the starting reference.
3. Check research publication's eight-window-per-group batch and specialist publication's 48-window batch. If they delay daily capture, reduce batch size or introduce bounded scheduling that prioritizes daily jobs; do not simply start more competing processes.
4. For publication failures, inspect the exact queue item, committed manifest and receipt. Repair input/schema/partition problems, then replay that window.
5. Close only after queue age/depth trends improve and affected source-filtered Athena queries succeed. Existing raw-table access does not establish specialist-table readiness.

Observed outstanding queue entries:

| Owner | Entries |
|---|---:|
| Specialists | 6,526 |
| Regulatory | 6,376 |
| People | 2,363 |
| Disclosures | 429 |
| Market | 266 |
| News | 190 |
| SEC | 65 |
| Conferences | 20 |

These are queue entries, not unique companies, missing rows or an ETA. Some require upstream completion or receipt reconciliation.

## 2. Previous authenticated-worker memory failure — implementation; verification pending

1. Inspect `capture_started` entries in `optima-authenticated-daily.service` to identify the source actually running before any new failure. The last successful source is not necessarily the failing source.
2. Replay through the existing scheduled runner under the new limits; measure peak memory, including the RAM filesystem.
3. If it still exceeds limits, stream/chunk the specific large response or document and reduce work per invocation. Preserve raw evidence and committed cursors.
4. Require the formerly failing scope's S3 commit and Athena receipt. No services currently marked failed is encouraging, but does not prove this scope recovered.

## 3. HKEX Excel filings — implementation; code fixed, partial live recovery

1. Retain the workbook-aware extractor in `disclosure_content.py`; both historical and daily failures pointed to XLSX bytes incorrectly passed to a text decoder.
2. Resume the original failed daily and historical scopes. January 3, 2021 already committed 30 filings and the dedicated backfill advanced to January 4.
3. Confirm document extraction preserves sheet names, cell coordinates and values, then publish those manifests.
4. Run the HKEX/document Athena checks and verify content references. Clear only the repaired scopes; the remaining `edinet_text_encoding_unresolved` label can be old HKEX evidence rather than an EDINET access problem.

## 4. MHRA duplicate records — implementation; code fixed, live verification pending

1. Retain separate identities for current and expired register assertions in `regulatory_sources.py`. Three expired-register designations also appeared in the committed current register.
2. Resume the failed stage; do not delete either assertion or assume which source register is correct.
3. Confirm all 60 saved expired-register rows have distinct IDs and the production window completes.
4. Publish and inspect both register status and designation ID in Athena; confirm downstream joins do not double-count the two assertions as separate medicinal products.

## 5. Dependent disclosures blocked by prerequisites — implementation

1. Read the blocked task's exact upstream manifest requirements (HKEX inventory, original documents or extracted content).
2. Complete the missing upstream scope using sections 3–4 where relevant; verify matching universe/date boundaries.
3. Resume document processing, then press releases, licensing agreements, M&A and strategic-transaction candidates.
4. Verify each output route in Athena. Never convert a blocked dependency into a successful empty result.

## 6. EMA/CTIS HTTP 400 — implementation

1. Locate the failed core-historical manifest and saved request/response; confirm EMA is the failing source before editing any adapter.
2. Inspect `EMA.page` in `regulatory_sources.py` and endpoint definitions in `ema_ctis_actions.py`. Validate request body, pagination and sort fields against the current official interface.
3. Correct the rejected parameter and run one bounded request. Keep total-count/date-order checks; split scopes if a genuine provider result cap is reached.
4. Resume and reconcile the window, then verify records in Athena. Do not treat pre-platform history as an empty, fully covered archive without evidence.

## 7. MHRA historical designation dates unavailable — implementation; coverage limitation

1. Identify which source rows lack an actual designation date; distinguish designation, expiry and removal dates.
2. Seek dated original documents or an authorized archive for those rows.
3. If dates cannot be established, retain the current snapshot and document the precise historical gap. Do not substitute retrieval, expiry or removal dates.
4. Publish supported fields and exclude unsupported historical features explicitly. This may end in a documented limitation rather than newly acquired data.

## 8. Market gaps — implementation; coverage review

Observed: 179 unresolved daily symbols, 208 historical symbols, 26 reviewed exclusions. The symbol sets may overlap.

1. Export unresolved symbol/date windows from both market lanes.
2. Check exchange/ticker mapping, IPO/delisting dates, trading calendars and provider availability against dated evidence.
3. Correct mappings and retry valid windows. For impossible windows such as pre-IPO prices, add a reviewed exclusion for that precise interval with evidence and reason.
4. Reconcile unresolved counts and inspect prices/actions in Athena. Exclusions must not conceal missing trading-day data.

## 9. News source changed during pagination — implementation

1. Inspect the failed news scope's page hashes, totals and cursor.
2. Confirm `news_operations.py` selected its bounded refresh path; preserve old committed observations.
3. Refresh the affected scope, splitting or reducing mutable windows if repeated changes prevent exhaustion. Keep provider quotas, including Finlight limits.
4. Verify unique article identities, completion coverage and Athena publication. Do not downgrade Finlight solely because retries or partial capture succeed.

## 10. Patent source changed during pagination — implementation

1. Separate patent daily and prosecution scopes; inspect saved counts/page hashes.
2. Confirm `patent_operations.py` or `patent_prosecution_operations.py` refreshes the affected scope rather than endlessly reusing the invalid cursor.
3. Use bounded date/entity splits where supported. Preserve previous versions and evidence.
4. Require fresh committed pages and source-specific Athena receipts; another patent job succeeding does not clear this scope.

## 11. Patent prosecution HTTP 403 — implementation; possible access dependency

1. Identify the exact USPTO endpoint, response and document type.
2. Check route and configured credential permissions without printing keys. Separate denied requests from source-change failures.
3. Test a minimal permitted request. If the provider explicitly requires additional access, give the user the exact product/permission request and denial evidence.
4. Resume the failed scope and verify office-action or petition records in Athena. Do not request a replacement key without an evidenced reason.

## 12. NMPA rendered source unavailable — implementation; provider diagnosis

1. Inspect the failed target page and Decodo response/status, including any async result identifier.
2. Check target availability, rendering parameters, account quota and completion polling. Distinguish a gateway failure from a target-page failure.
3. Test one page and require the expected inventory/detail identifiers before resuming pagination.
4. Verify cursor advancement, S3 records and Athena output. The paid plan alone does not establish successful rendering.

## 13. Reddit HTTP 500 — implementation; retries added, live verification pending

1. Let the updated collector perform its maximum three attempts within the existing request budget.
2. If all fail, identify the failing route and narrow request size/scope; retain the bounded retry policy.
3. Preserve content revalidation and expiry behavior. A shrinking retained sample during failed revalidation is not proof that historical capture succeeded.
4. Confirm fresh posts/comments and successful Athena verification. Do not clear the error merely because older cached data is readable.

## 14. Bluesky/social HTTP 403 — implementation; possible access dependency

1. Identify the denied search endpoint and exact account/route configuration in `people_social_collection.py`.
2. Verify whether that endpoint needs authentication or a different supported API route.
3. Test one bounded request; if additional access is necessary, document exactly what the provider requires before assigning the user a task.
4. Resume and verify source-filtered Athena rows. Do not claim a complete historical archive from a search sample.

## 15. EIA generator workbook returns HTML — implementation/provider issue

1. Inspect the September 2026 workbook URL and original HTTP response; both indexed archive and same-month nonarchive probes returned HTML with HTTP 200.
2. Check the official EIA index for a valid same-period file; verify ZIP/XLSX signature, report period, sheets and required columns.
3. If the file is unavailable, record that period as pending/unavailable and retry at a bounded cadence. Do not silently substitute another month or accept HTML as an empty workbook.
4. Once available, replay the exact scope and verify generator identifiers, battery rows and units in Athena.

## 16. Authenticated historical transport/quota failures — implementation

Retained scopes include EIA retail transport/HTTP 504, SAM.gov HTTP 429 and FDA iRES HTTP 503. Some attempts date from October 18–19.

1. Reconcile each failed scope against newer successful manifests; avoid unnecessary duplicate capture.
2. For SAM.gov, respect the shared hourly/daily quota and provider retry timing. For EIA/FDA, use bounded transient retries and smaller requests where supported.
3. Resume only the failed scope through the existing lane, preserving pagination and counters.
4. Verify S3 output and the relevant Athena source. Ask for user access changes only if an actual authorization error remains.

## 17. TED record exceeds batch-size limit — implementation

1. Locate the oversized notice and inspect the normalized record size versus the 8 MiB batch limit.
2. Preserve the original XML. Avoid repeating full XML, full parsed tree and repeated extracted fields in one oversized observation; store referenced content or bounded chunks with notice/lot/context identity.
3. Update downstream readers and tests so no values, currencies, parties or lot relationships are silently lost. Do not just truncate or globally remove the size check.
4. Replay the uncommitted page, verify notice counts and references, then query the resulting structure in Athena.

## 18. NIH RePORTER HTTP 404 and result cap — implementation

1. Inspect each failed endpoint/request and distinguish a missing route from a valid zero-result search.
2. Correct the official endpoint/version if needed and verify a small request.
3. For `nih_result_cap_split_scope_required`, split into supported narrower date/fiscal-year/entity scopes; record split coverage and deduplicate stable grant identities.
4. Reconcile counts across all child scopes and publish to Athena. One successful child does not complete the parent window.

## 19. CAISO column mismatch — implementation; older retained scope

1. Read the saved ZIP/CSV and requested report/market variant for `caiso_columns`.
2. Compare its headers with the current `caiso_enrichment.py` parser; determine whether the response is a different report or a schema change.
3. Add a tested mapping only for validated columns, preserving interval timezone, node, market, price component and units.
4. Replay the exact scope and verify those fields in Athena; check dedicated CAISO worker receipts for an already-completed replacement scope first.

## 20. GitHub SDK HTTP 422 / hourly request budget — implementation

1. Inspect the failed repository/query and validation response for HTTP 422; fix invalid search terms, dates or parameters.
2. Treat `github_public_hour_budget` as a quota deferral, not a reason to bypass counters. Resume after reset and verify fair progress across SDK/MLPerf jobs.
3. Run one bounded request and preserve repository, commit and artifact provenance.
4. Verify the affected scope's Athena rows. Reconcile older failed scheduler entries with dedicated enrichment results.

## 21. USGS minerals and Europe PMC full text retry exhaustion — implementation

1. Identify the specific publication/document URL and saved response.
2. Check the current official download route and whether the full text is actually available for authorized retrieval. Handle unavailable documents explicitly.
3. Repair changed links or use bounded retries; retain metadata and a coverage reason when full text cannot be obtained.
4. Verify content checksum/provenance and Athena-accessible references. Do not mark metadata-only records as complete full-text capture.

## 22. CPSC missing recall identity/date — implementation

1. Inspect the raw response for the failed historical recall record.
2. Determine whether required fields moved, have a different format, or are genuinely absent.
3. Add a validated mapping or preserve the malformed record as an explicit gap; do not invent IDs or dates.
4. Replay the scope and verify recall identity/date completeness in Athena.

## 23. EDINET ZIP expansion limit — implementation

1. Inspect the saved archive's compressed/uncompressed sizes, member list and exact failed filing.
2. Stream member extraction or split extracted content into referenced artifacts while preserving XBRL contexts/units and document provenance.
3. Keep archive/member safety limits and test peak memory under the new shared budget; more RAM is not justification for unlimited decompression.
4. Resume the same filing and verify all advertised supported document formats and Athena content references.

## 24. Retained disk-full and interruption failures — implementation; retry verification

Affected saved scopes include GitHub SDK, MLPerf, TED, USPTO assignment history and SAM.gov; specialist daily also retains `KeyboardInterrupt`.

1. Check each attempt timestamp against the disk migration, request-gate repair and upgrade maintenance window. Planned SIGINT shutdowns are not automatically new defects.
2. Confirm free disk/RAM space and a valid S3 checkpoint; recover retained state before replay if needed.
3. Resume the exact failed scope. The USPTO request-gate atomic-write repair is already deployed; verify production use rather than repeating the fix.
4. Require new committed output and Athena publication before clearing the old scope. Never delete failure evidence merely because storage is now available.

## 25. SMS delivery — user + AWS; awaiting review

1. Wait for the current registration review. AWS reports **REVIEWING** after your URL change.
2. If rejected, share the new reason; make only the requested correction and resubmit.
3. Once approved, confirm sender readiness and positive delivery evidence from a scheduled notification.
4. Until then, do not interpret an idle delivery alarm as successful SMS delivery. No additional purchase is currently indicated.

## Not collection errors: downstream stages awaiting setup

The health registry marks event pipelines, specialist models, HMM, TFT training and TFT testing as `awaiting_setup`. This is registry status, not proof that no related code exists.

1. Inventory existing implementation and required input contracts for each stage.
2. Validate required source fields and coverage using the Athena SQL checks.
3. Configure the stage's execution schedule and artifact/validation receipts when its prerequisites are ready.
4. Verify outputs before changing its registry status. These stages are separate from draining collection history.

## Standard verification for every repair

1. Record the failed source, task/window ID, manifest and reason from the supplied evidence files.
2. Repair and test with the preserved raw response where possible.
3. Resume through the existing supervised runner. Do not reset global cursors, bypass quotas or launch an overlapping writer.
4. Verify a committed S3 page/final manifest and publication receipt with matching scope and checksums.
5. Query the intended Athena table for that source/window; inspect identifiers, dates, units, content references and specialist-required fields. Use the existing `SQL-checks.md`; do not count monitoring status rows as data.
6. Mark the exact scope recovered, retaining unresolved coverage and the original failure audit trail.

Evidence: `health-evidence.json` and `scope-evidence.json` beside this guide. The latter contains source, manifest, job parameters and last-attempt timestamps for retained specialist failures. No credentials are included.
