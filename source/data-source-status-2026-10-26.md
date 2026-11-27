# Data-source status — refreshed 24 November 2026

## November 24 — current actions and recovery

**Your actions:**

1. **Send EODHD the [prepared invalid-price report](data-collection-processing/repair-notes/2026-11-23-shutdown-recovery/EODHD-support-message.txt).** Ask for corrected raw OHLC for the listed dates/symbols. The retained evidence has 408 inconsistent bars across five symbols. Share their response; no new subscription is requested.
2. **If available, confirm SAM.gov's daily allowance** in your account or send [this enquiry](data-collection-processing/repair-notes/2026-11-23-shutdown-recovery/SAM-support-message.txt). We retain the conservative 10/day cap meanwhile; collection has resumed without a replacement key.
3. Continue your Athena payload reviews. Report missing fields or wrong shapes; passing a readback does not prove specialist-layer suitability.

**Repaired:** the missing shared RAM workspace caused services to fail before running. Restored it and added a per-start existence check to 66 units. Two real namespace regression tests and 12 workspace tests passed. SAM, ChiCTR, news and people have fresh commit/checkpoint evidence; patent gap catchup resumed. Deliberately paused sources remain paused.

**Athena verified today at 17:52 UTC:** 147 fresh queries succeeded, covering 140 source/dataset pairs; sampled S3 checks also passed. These validate existing published records. Newly captured batches and active publication queues still need their own receipts/readbacks.

**Engineering still outstanding:** continued disclosure catchup (the fresh monitor has no active prerequisite alert); active worker publication; product-search registry selection exceeding its ten-second database limit; code-backup selection rejecting a generated >10 MiB tokenizer. A separate EDINET document-format failure and a Health Canada daily timeout also need targeted investigation/replay. These are engineering work, not requests for you to rotate credentials or restart jobs. Market coverage remains 174 daily / 491 historical symbols with unresolved windows; do not confuse that broad count with the five confirmed invalid-price symbols.

[Detailed repairs, evidence and limits](data-collection-processing/repair-notes/2026-11-24-service-checkup/README.md). Earlier dated entries below are history, not today's action list. SMS is working and needs no action.


## November 23 — recovery after the controller reboot

**Verified:** both instances are running; all **15 historical executors** are running; controller intake/health timers and metadata workers are active. Fresh metadata acceptance and publication occurred after the reboot. An actual Athena readback returned **32 rows, all linked to raw objects**, matching a newly verified publication receipt. [Run the tested query](data-collection-processing/repair-notes/2026-11-23-shutdown-recovery/metadata-athena-check.sql). This is a tested path, not a claim that every source/history is complete.

| Reported issue | Repair / evidence | Remaining work |
| --- | --- | --- |
| **Assignment history signal** | Latest service runs succeed. Added a verifiable already-complete summary for the exact configured reviewed scopes, rather than silent idle success. | Historical scope is eight applications / 88 year-application windows through the configured October 10 cutoff. Publication and broader assignment coverage remain separate. |
| **SAM source changed** | Fixed recovery of partial changed-source checkpoints. The exact replay recovered **4,000 records**, then hit provider HTTP 429. Four batches were handed to its enabled metadata source. | Cap is conservatively **10/day** until the account allowance is confirmed. Await quota reset and resume; no new key is needed. Not yet Athena-verified here. |
| **Disclosure prerequisite** | Batched rejected-parent checkpoints to remove excessive S3 writes. October 14 completed: **10 documents**, four M&A candidates and four strategic-transaction candidates; two other categories had zero matches. | Those scopes are queued; verify publication/readback. Continue HKEX and other dependent dates without bypassing prerequisites. |
| **Market OHLC inconsistency** | Verified **408 bad bars across five symbols** in provider responses. Added exact date/OHLC diagnostics and retained strict validation. Other symbols continue. | Provider correction or a separately evidenced route is needed; do not invent prices or waive these as impossible periods. |
| **Health Canada daily timeout** | Replay succeeded: **38,393 unique notices** reconciled against the full current report. No failed worker systemd units remained afterward. | Queued publication still needs its own readback. This is not a historical-vintage completeness claim. |

**Your two follow-ups:**

1. Confirm the SAM account's daily API allowance with its account/role information or Federal Service Desk. [Ready-to-send question](data-collection-processing/repair-notes/2026-11-23-shutdown-recovery/SAM-support-message.txt). Share the allowance, not the key.
2. Ask EODHD to correct inconsistent OHLC for `2311.TW`, `2325.TW`, `3559.TW`, `ABB.MC` and `DD.MX`. [Ready-to-send report with examples](data-collection-processing/repair-notes/2026-11-23-shutdown-recovery/EODHD-support-message.txt).

**Shutdown finding:** the controller rebooted at **16:18 UTC**, following an out-of-memory trace at **16:16:51 UTC**. The retained log does not identify the final victim or prove the complete cause. No resize was applied. Current memory availability was about 1.9 GiB, and bounded repair jobs retained their resource caps. M7's latest boot preceded the controller event.

**Final checks:** no failed systemd units were found on either host; the health service and metadata controller completed successfully. The old assignment alert cleared on verified scope evidence. Six low-severity incidents remain; **no active high alerts** were found.

**105 tests passed.** [Recovery evidence and exact limitations](data-collection-processing/repair-notes/2026-11-23-shutdown-recovery/README.md). Existing owner pauses and 15 non-enabled metadata registry entries (including internal access-layer routes) were retained; no blanket “all pipelines healthy” claim is made while provider errors and unverified publication remain. This section supersedes the older current-state counts below.

## November 20 — high inspection alert resolved

**No action needed from you.** The monitor could not save its optional verification cache inside its read-only service sandbox. A dedicated writable cache directory fixed this. The actual health service completed successfully, saved its cache and published an error-free report; the high inspection incident was reconciled. This did not require restarting collectors or changing API/IAM permissions. [Evidence](data-collection-processing/repair-notes/2026-11-20-inspection-alert/README.md).

## November 20 — service repairs and your actions

**Your actions:** no new key, purchase, IAM change, manual restart or new exception is requested. Continue existing Athena field checks if useful. SMS is working.

| Priority | Finding / fix | Remaining verification |
| --- | --- | --- |
| **Regulatory publication** | The installed November 18 patch wrote its scan cursor outside the worker's allowed S3 paths. Corrected the cursor to the existing `publication-retries/` metadata prefix, retaining bounded rotation and conditional writes. No permission expansion. | **Staged for the next normal worker session.** Verify the included real permission probe, cursor advancement and successful publication/Athena receipt before closing AccessDenied. |
| **Patent daily capture** | November 10 is stuck in a changing **04:00–04:03:45** subrange. The old five-minute split floor prevented further subdivision. Recovery now permits smaller ranges, retaining completed hours and all request/validation limits. | **Staged, not live-verified.** Check fresh committed progress beyond the affected child, then complete/publicise the exact day. The parent's 30,939 saved records do not mean the day is complete. |
| **CMS/FDA monitoring** | Corrected historical worker timestamp translation during sleep and added exact CMS/FDA scoped queue/receipt checks, including manifest, checksum and window identity. An empty successful invocation is insufficient proof by itself. | **Verified all 10 CMS and 168 FDA review windows** against their own receipts; the two old process alerts cleared. Other unmatched scopes remain unresolved. |
| **Other service work** | CMS/Crossref backlog, old assignment/NIST failures without adequate recovery evidence, authenticated-source 429s and unresolved market windows remain. | Independently replay/verify the named scope. Market's last inspected counts are **174 daily / 201 historical symbols**, with **56 reviewed exclusions**. |

**Current worker schedule:** intentionally asleep; **30 requests** are retained. Earliest queue-threshold wake is **17:57 CET today (November 20)**; pending work triggers a wake by **03:57 CET tomorrow (November 21)** under the existing policy. The deployment timer waits for that normal boot; it does not start an extra session. These times are wake bounds, not repair-completion guarantees.

The final refreshed overview reduced service groups needing attention **16 → 8**, with zero inspection errors. The scoped receipt verification is recorded in the [repair evidence](data-collection-processing/repair-notes/2026-11-20-service-checkup/README.md). **123 tests passed.** Live worker installation and replay verification remain pending; no historical gap was cleared merely to reduce alert counts. This section supersedes older current-state summaries below.

## November 18 afternoon — latest email and your tasks

**Your task today:** no new key, purchase, permission change or manual restart is requested. If you want to continue review, run the [new FDA sample query](data-collection-processing/repair-notes/2026-11-18-afternoon-checkup/FDA-random-sample.sql) and check the fields needed by the specialist layers. **1,203 rows across these three windows passed a fresh Athena readback**, with populated payloads. SMS is working.

| Priority | Current finding | Engineering follow-up |
| --- | --- | --- |
| **Regulatory publication** | Six of 54 repaired FDA windows have verified receipts; **48 remain**, and the repaired ClinicalTrials window is still queued. The latest publisher failure was S3 `SlowDown` during queue metadata reads. | A tested 128-candidate rotating scan and lower read concurrency are ready. Deployment is scheduled for M7's next normal boot; **not installed or live-verified yet**. Finish publication/readback afterward. |
| **Unverified execution failures** | Historical service exits, provider 429s and publication failures without recovery proof remain visible. | Replay/check their exact scopes during the next session; do not close them on an empty successful invocation. |
| **Finlight, HKEX/disclosures and market** | Mutable news pagination, incomplete prerequisites and unresolved price coverage remain. | Continue the morning repairs independently; retain scoped gap evidence. No additional API purchase is requested. |
| **Historical source gaps** | Zenodo, PortWatch, MHRA, DataCite, CTIS, WTO, USAspending, preprints, NHSBSA, UNIDO and Copernicus still have retained gaps. | Work through exact scopes; distinguish actual source limitations from recoverable errors before excluding anything. |

**Monitoring fixed live:** M7 is deliberately in scheduled batch sleep. Its old snapshot is now historical evidence rather than a separate inspection failure for every service. **Zero inspection errors** remain in the refreshed report; active service groups fell **26 → 13**. Source failures and historical gaps were retained. Scheduled sleep is explicitly shown, without claiming that stopped services are currently running or healthy.

**Next normal session:** M7 may wake from **03:50 CET Thursday, November 19**, if its queue threshold is met; pending work triggers a wake by **13:50 CET** under the existing maximum-off policy. **27 durable requests** are queued. These are wake bounds, not completion promises. No extra instance session was started. The bounded deployment timer handles the pending patch automatically and records success or failure.

**79 tests passed.** [Afternoon repair evidence and limitations](data-collection-processing/repair-notes/2026-11-18-afternoon-checkup/README.md). Earlier entries below are retained history; this section supersedes their current counts.

## November 18 checkup — current repairs and your actions

**Your actions today:** no new API key, purchase, IAM permission or manual restart is requested by this checkup. Continue your Athena payload reviews using already verified SQL. Report missing specialist fields; queued captures are not yet verified Athena data. SMS is working and is not an action item.

| Priority / source | Current state | Next engineering step |
| --- | --- | --- |
| **Publication backlog** | Only 3 of the 54 repaired FDA windows have verified publication receipts. The other 51 remain queued. A bounded continuation is running with durable logs, three-window batches and the existing global lock. ClinicalTrials August 2022 and PortWatch January 20, 2019 have also been queued. | Finish publication and run partition-bounded Athena readbacks. Do not mark these newly captured batches Athena-verified yet. |
| **Finlight news** | The supported controller route runs, but November 17 still fails its pagination consistency check. Three component scopes are complete; a later scope remains mutable. Its one-refresh-per-UTC-day limit and existing request budget remain enforced. | Resolve the remaining mutable scope; verify subsequent publication. No replacement credential is requested. A manual worker probe could not read `newKeys`; it is not the configured controller route and no IAM expansion was made. |
| **HKEX / dependent disclosures** | Repaired the mismatched validation ceiling: the official downloader and validator now both allow 128 MiB. The failed October 7 replay advanced to **313 committed records**, stopping at its three-page budget rather than the oversized-document error. | Continue this date, complete prerequisite manifests and publish/verify dependent disclosures. |
| **Market coverage** | Latest inspected health report still lists **174 daily / 201 historical symbols**, with **56 reviewed exclusions**. These counts have not been revalidated symbol by symbol in this pass. | Investigate mappings and genuine missing prices; add exclusions only with evidence. |
| **Other historical failures** | TED's November 2016 stale iteration now restarts safely and committed **200 records** before its two-page budget. Other source/date groups remain unresolved. | Continue TED; repair/replay the remaining EMA, DataCite, Zenodo, WTO, NHSBSA, USAspending, UNIDO, EDINET and weather scopes independently. Preserve raw-validation holds and intentional source pauses. |
| **MHRA historical dates** | A fresh official Innovation Passport spreadsheet contains eight rows with company, product and indication fields but no designation-date column. This is evidence of a source limitation, not proof of a full historical archive. Daily snapshots remain useful. | Separate undated current-register evidence from dated historical capture; do not invent dates or declare all UK history complete. No owner credential action is needed. |

**Completed in this pass:** ClinicalTrials.gov August 2022 captured and reconciled **3,290 records**; PortWatch January 20, 2019 captured **2,071 records**. Census October 2026 now reports `census_period_not_yet_published` rather than the old HTTP 503; it remains incomplete and should wait for release.

**Monitoring repaired:** the summary worker lacked a collector-only import, causing exact FDA completion proofs to be silently ignored. Task hashing is now self-contained and tested. All 54 repaired FDA windows were checked against their complete manifests and checkpoint histories; **31 recurring FDA intervals** were removed from the cached report with an immutable backup. Its remaining flagged historical intervals fell **109 → 78**; this was a targeted reconciliation, not a fresh audit of every other source. Capture completion and Athena publication remain separate checks.

**Worker check:** all **15/15 executors** are online and the metadata streaming timer is active. The full historical-audit diagnostic exceeded its 10-minute limit; optimising that audit remains engineering work. The 109 → 78 count above comes from the separately verified FDA reconciliation, not a completed full audit.

**34 regression tests passed.** [Repair notes, results and remaining limitations](data-collection-processing/repair-notes/2026-11-18-checkup/README.md). EDINET 2016 remains excluded. Reddit, Bluesky, GitHub source capture and Marketaux remain paused. The approved residential PDF fallback keeps its existing shared four-attempt/day cap.

## November 18 — residential PDF fallback enabled

**No action remains for this setup.** The replacement password passed live PDF validation, and the explicitly approved fallback is enabled for the 12 named public-PDF collectors. Existing downloads, validated cache and an ordinary HTTPS retry precede the residential proxy.

**Cost limits:** four paid attempts per UTC day **shared across all sources/hosts**, 8 MiB per PDF, one paid attempt per URL per day and one per collector client. Failures count; there are no paid retries or paid redirect chains. Two validation downloads count toward today's allowance. Budget exhaustion defers only the affected PDF; other capture continues. Missing/authentication/rate-limit/oversized responses do not trigger paid traffic.

**151 tests passed**, plus live downloads and worker cache/shared-quota checks. No account purchase, IAM change or production-cache seed was needed. Other sources and private/signed/extensionless download routes remain outside this rollout. This does not certify historical completeness or Athena publication. [Approved sources, evidence and rollback](data-collection-processing/repair-notes/2026-11-18-pdf-fallback/README.md).

## November 18 — Decodo proxy login verified

**The standard HTTPS proxy now downloads valid original PDFs from both controller and production worker.** The control PDF and 49-page medRxiv PDF matched the direct originals byte-for-byte, with strict parsing and DOI verification passing. [Results and validated PDF](data-collection-processing/repair-notes/2026-11-18-decodo-proxy/README.md).

**Completed:** the proxy password was regenerated and verified; the approved fallback is now enabled. The previous instruction was to update only `decodo-proxy-password` in the existing `proxies` secret. The initial endpoint-parsing diagnostic accidentally exposed the login in its error output. The endpoint was corrected to contain only host and port; do not put credentials back into that field. No new subscription or API key is needed. The password was replaced and rechecked; current activation and cost limits are recorded above. This is a verified download transport, not a claim of complete preprint collection or Athena publication.

## November 18 — PDF download test

**The previously blocked medRxiv PDF now downloads directly on both the controller and production worker.** The existing downloader returned an identical 781,135-byte, 49-page PDF, with strict parsing and DOI verification passing. [Download the validated sample](data-collection-processing/repair-notes/2026-11-18-decodo-pdf/medrxiv-direct.pdf).

Two new bounded Decodo API tests still returned JSON text instead of usable PDF bytes, including a small known control PDF. Keep that fallback disabled. No production configuration or Athena publication changed. A standard proxy route remains untested because only scraping API credentials are stored; account entitlement is unknown. **No purchase is requested.** Separate proxy credentials are needed only if an included proxy fallback is to be tested. [Results and exact next step](data-collection-processing/repair-notes/2026-11-18-decodo-pdf/README.md).

## November 16 afternoon — latest email repairs

**Your actions:** continue the Athena samples below. **Decodo support task closed:** you confirmed that base64 output is not available. The tested PDF route remains disabled; the alternative download transport is engineering work. No further base64 support request is needed. **No new API key, IAM change, purchase or manual restart is currently requested. SMS is working.**

- **FDA:** all **54 monthly windows listed in this checkup now capture successfully**, with **21,380 observation occurrences**. Fixed incompatible old cursors and CRL identities for bundled PDFs containing several letters. February–April 2016 are **published and verified in Athena: 1,285 records**, including a fresh payload read. [Run the verified FDA SQL](data-collection-processing/repair-notes/2026-11-16-afternoon-checkup/FDA-Athena-check.sql). The other 51 repaired windows remain publication/verification work; this is not a claim of complete FDA history.
- **Finlight:** corrected the stale recent-only setting; the stuck October 10 reconciliation completed all eight configured scopes and was queued. Daily capture is caught up through November 15. The new reconciliation still needs publication verification.
- **EIA:** corrected the worker metadata path and resumed the affected scope from 30 to 40 records. It remains a bounded continuation, with no permission expansion.
- **Patents:** the newer office-action download failure replay recovered and advanced from 975 to 980 records. The regular prosecution service was resumed; no new exclusion or key was needed. Separate daily pagination recovery remains open.
- **Monitoring:** exact committed FDA repairs removed 31 merged gap intervals. Another 188 Copernicus capacity waits are retained as backlog. That historical snapshot now has **94 actionable intervals, down from 313**; these are not service counts. Transient database admission failures now have bounded retries with rate limits still enforced.

**177 regression checks passed.** Remaining engineering work includes the other FDA publications, HKEX/disclosure prerequisites, market coverage, other historical pagination failures and weather extraction. No raw-validation holds or intentional source pauses were lifted. EDINET 2016 stays excluded. See the [latest repair notes and evidence](data-collection-processing/repair-notes/2026-11-16-afternoon-checkup/README.md).

## November 16 — today's actions and remaining repairs

**For you today:** completed repairs need no new access. The Decodo Bearer key is configured and works; support confirmed that base64 is unavailable. The PDF transport issue is now engineering work, not a support follow-up for you. No new paid plan or larger instance is currently requested. **SMS works; it is not an action item.**

1. Inspect the recovered **USGS 2019 cobalt report** and **PortWatch January 23, 2019** rows using the two partition-bounded queries in the [November 16 repair notes](data-collection-processing/repair-notes/2026-11-16-checkup/README.md). Both scopes have passed actual Athena verification; PortWatch contains **2,065 observations**. Report any specialist fields you expect that are absent.
**EDINET 2016: excluded by your decision on November 16.** The archive is not required, has no acquisition task, and must not generate actionable alerts or API retries. Saved evidence remains retained. Other EDINET years and current daily capture remain in scope.

2. **Decodo support follow-up is closed.** The owner confirmed that base64 output is not offered. The supplied Bearer key works, but the tested raw string failed strict PDF reconstruction. Keep this PDF route disabled; do not repeat paid probes or request another Web Data API key. Investigate direct/authorised archive downloads or a binary-preserving proxy transport. Proxy access under the existing plan and success on the target remain unverified; no new purchase has been requested. [Current findings](data-collection-processing/repair-notes/2026-11-16-decodo-web-data/README.md).

**Highest remaining implementation work:** finish HKEX/disclosure recovery; replay the exact FDA/EMA/ClinicalTrials historical gaps; investigate medRxiv's continuing PDF 403; stabilize Zenodo/DataCite pagination; finish weather extraction and market mapping/gap review. These are not instructions for you to restart services or purchase access.

**Changed today:** recovered eight older empty Census queries using positive same-month controls; kept ten unpublished October scopes incomplete and retryable. Recorded eleven impossible ALFRED vintage requests, 41 pre-launch medRxiv scopes and two invalid historical WTO requests as evidenced exceptions. EDINET now has a narrowly checked retention exception, with all **300 expired failed days classified**. Finlight capture recovered. Two Copernicus NetCDF scopes committed; structured weather fields remain a separate requirement. Fixed HKEX's identified 90 MB PDF limit, completed its **1,367-row index / 1,411 observations**, and completed **six selected disclosure documents**. Candidate outputs and downstream publication still require verification. Replaced the publisher's unbounded inventory scan with a resumable 128-entry pass and restarted that scan safely. All **12 recovered windows are now published and verified in Athena**, including eight empty Census coverage partitions and two Copernicus raw-artifact observations. Capture is not treated as complete publication; structured weather extraction and other historical/derived scopes remain open.

See the [repair notes and owner steps](data-collection-processing/repair-notes/2026-11-16-checkup/README.md) for exact evidence, open engineering tasks, SQL checks and durable logs. Earlier dated snapshots below remain historical evidence, not a claim that every source is ready today.


## November 14 — six existing raw-data/SQL sources rechecked

**Entries 50, 53, 55, 56, 57 and 58 are marked reviewed for their existing raw materials and SQL visibility.** Twelve sampled records passed official-original comparisons, checksums and collection-commit checks on m7. Fresh committed-data and metadata previews returned substantive records for every source. Verified published observation snapshot: USGS **84**, EIA battery generators **13,085**, EIA retail prices **322**, CAISO prices **16,256**, BLS wages **802**, ROR institutions **141**. Counts are occurrences, not unique records, full archives or certification of all derived conclusions.

**Open finding: USGS metadata remains stopped** after four older raw-validation failures and has one missing-object retry. Current sampled original reports and published SQL pass; this review does not resume that queue or clear those findings. Older missing-checkpoint inputs for battery, CAISO, BLS and ROR, plus one old ROR receipt failure, remain recorded. No source pauses, contracts, queue states or production limits were changed. No owner action is required to complete this review. [Verified SQL](data-collection-processing/repair-notes/2026-11-14-six-source-review/review-queries.sql) · [Evidence and remaining findings](data-collection-processing/repair-notes/2026-11-14-six-source-review/review-complete.json).


## November 13 — UN Comtrade and DOE storage reviews completed

**Entries 51 and 52 are reviewed for their scoped raw-validation, metadata and Athena pipelines.** Fixed false generic raw stops, missing DOE companion contracts, the public-document receipt adapter and metadata publication contention. All five source streams are enabled; all 20 formerly failing batches are accepted and published. Replaced 831 old queue entries with 754 distinct contract jobs. **61 tests passed**, plus 53 saved-input validations, four older historical-input checks and an Athena readback of the archived storage report.

Verified SQL snapshot: **14 Comtrade observations and 54 DOE observations** across program/documents/technical/funding streams, all raw-complete for their declared kinds. Latest Comtrade and program inputs are from November 13; saved DOE companion inputs extend through November 11. Counts are occurrences, not unique flows/documents or complete history. Storage-only discovery now has working daily and historical frontiers; old unrelated files are retained but excluded. The retired tracking-based enrichment stays retired. One old uncommitted DOE input remains excluded.

**All 75 enabled timers and 15 historical executors checked healthy; metadata/streaming lanes active.** The full indexed diagnostic completed: 448,882 job records, 161 metadata sources and 123 historical routes, 494 queries, maximum query time 0.8665 seconds, no query retries. It still records **51 other raw-stopped sources, 21 blocked historical attempts and 34 retryable historical attempts**; these are not cleared by this review. Intentional pauses remain. No new IAM, key or manual restart is needed for entries 51/52. [Working SQL](data-collection-processing/repair-notes/2026-11-13-comtrade-doe/review-queries.sql) · [Review and remaining holds](data-collection-processing/repair-notes/2026-11-13-comtrade-doe/review-complete.json).


## November 13 — GitHub App installation is blocked in GitHub

The owner sees **“No accounts available”** when installing the valid App 5743112. Live API checks still show owner `rmalc5150` and zero installations; the public owner-profile endpoint also returns 404. **Confirm the browser is signed in as `rmalc5150`. If it is, contact GitHub Support** with the updated [diagnostic](code-backup/README.md). The precise eligibility/access restriction is not confirmed. App authentication code is ready, but no App-backed push has succeeded and production authentication has not switched. This supersedes the earlier “installation required” instruction below.


## November 13 — GitHub App ready; installation required

**Your next step:** install **Optima EC2 Backup** on `rmalc5150/semaphore`: [open Install App](https://github.com/settings/apps/optima-ec2-backup/installations), choose your account, select **Only select repositories → semaphore**, and click **Install**. App ID **5743112** and the Secrets Manager private key authenticate successfully, with Contents: write permission, but GitHub reports **zero installations**. This missing setup step is separate from the old SSH issue.

The worker's App authentication path is implemented; **eight tests and the production credential/source-selection scan passed**. It uses temporary repository-scoped tokens over HTTPS and independently checks the remote commit after pushing. No App-backed push has occurred and production has not switched yet. After installation, the remaining engineering steps are the actual backup push/readback and activation of the daily service's App configuration. See [setup and recovery notes](code-backup/README.md).


## November 13 — Trade screening Athena review completed

**Entry 49 is reviewed for SQL visibility and publication.** The old preview explicitly used `LIMIT 1`; the aggregate query returns one summary row by design. A separate real backlog was repaired: **18 accepted batches / 576 observations** are now published and verified in fresh Athena queries. Added this source to the existing bounded reviewed-source publisher on m7.

The verified snapshot contains **897 observations: 896 named screening entries and one older archive receipt**, with complete raw status for their declared kinds. The replacement query returns 25 individual entries and retains full provider fields and original-evidence links. These are observation occurrences, not unique entities or complete history. Source processing is enabled; recurring publication and streaming timers are active. Ten old inputs missing checkpoint evidence and one discovery-only receipt remain excluded, and retired tracking enrichment stays retired. No IAM update or manual restart is required from you. [Review evidence](data-collection-processing/repair-notes/2026-11-13-trade-screening/review-complete.json) · [working SQL](data-collection-processing/repair-notes/2026-11-13-trade-screening/review-queries.sql).


## November 13 — Federal Register raw-data review completed

**Entry 48 is reviewed for the configured raw-validation, metadata and SQL pipelines.** Both `federal_register` listings and `federal_register_documents` full notices are enabled under corrected contract 2.0.3. Fixed the generic raw-validation false stops and missing companion-document contract. Full notices require matching API metadata, original XML/HTML and official PDF; listings remain distinctly labelled metadata.

Verified Athena snapshot: **145 listing observations and 16 full-notice observations**, all raw-complete for their declared kinds. Checked 100 saved inputs: 99 inputs / 446 rows passed and one incomplete large notice was recaptured and verified. Notice 2026-22743 now links its full 120,719,355-byte PDF and 4,375,819-character extraction. Preserved the old partial raw capture and resolved its replacement lineage. Future PDF failures remain retries. **83 focused tests passed.**

All 15 historical executors, metadata lanes, streaming lane and enabled collection schedules were checked. A timed-out bounded patent continuation was successfully retried. Other source validation holds, intentional pauses and the deferred GitHub backup remain. This review covers the configured four search topics and companion notices; full archive completion, current-law status and product applicability are not certified. No new IAM edit, key or manual restart is required from you. [Review evidence](data-collection-processing/repair-notes/2026-11-13-federal-register/review-complete.json) · [working SQL](data-collection-processing/repair-notes/2026-11-13-federal-register/review-queries.sql).

## November 13 — GitHub source backup still needs owner access recovery

**Not restored:** the backup key authenticates as `rmalc5150/semaphore`, but live repository read and write probes both return `Repository not found`. No actual push succeeded. The daily backup timer is already enabled and active; its next attempt is November 14, 03:00 Europe/Madrid. A new credential-scanned, checksum-verified **4,014-file local snapshot** is saved under `code-backup/.pending/`; it has not been uploaded.

**Your action:** open the repository as its owner and complete any remaining account-recovery notice. The URL and deploy key were already confirmed/re-added yesterday. If they are unchanged and the repository is visible in your browser, ask GitHub Support to investigate the authenticated read/write denial; the exact cause is unconfirmed. [Step-by-step instructions and ready-to-send diagnostic](code-backup/README.md). The replacement deploy key was added and tested: SSH authentication succeeds, but read/write and SSH-over-443 still return `Repository not found`. Since you authorized switching only if it works, the production key was not changed. No push succeeded; contact GitHub Support with the updated diagnostic. The separately paused GitHub data collector remains paused.


## November 13 — oversized inputs, news, market and patent monitoring

**No new account/key/purchase or manual restart is needed for these repairs.** Large inputs now use a separate disk-backed worker with a 768 MiB memory cap; ordinary collection continues. Actual Athena readbacks cover repaired trade-screening, CORDIS, BIS, HKEX, FAOSTAT, Indonesian mineral, university-report and personnel inputs. Archive validation preserves originals and provenance; it does not imply every document/file is already converted into specialist analytical fields or that history is complete.

**Verified:** recovered Finlight window has **1,111 articles / 1,245 observations** in Athena. Repaired `AAPGV.US` → `AAPG.US` pricing has **218 Athena price rows** across four windows, and the exact US pre-IPO period is now excluded with issuer evidence. Removed a duplicate daily patent timer that conflicted with the canonical checkpoint; the canonical job committed progress. Normal partial request allowances no longer appear as source failures. **79 regression tests passed.** Temporary controller publication memory limits were restored after both repair checkpoints passed.

**Still needs attention:** **174 daily / 201 historical market symbols** need individual coverage/ticker/date evidence; see the saved listing/date inventory. Patent source-change refresh still needs its next committed recovery check; its service is scheduled. The bounded streaming/publication backlog continues. Four other personnel parent-content gaps, an unrelated HKEX original HTTP 404 and news payloads with full text pending remain explicit; they were not marked complete.

**Your optional verification today:** open the Athena queries/results linked in the [repair report](data-collection-processing/repair-notes/2026-11-13-streaming-alerts/README.md), inspect the market mapping and news payloads, and share issuer/exchange evidence for remaining market windows if you have it. Unresolved source coverage remains an engineering review task; do not buy another API or restart services solely for these alerts. Existing owner-paused sources remain paused. Older unrelated access/licensing tasks below are unchanged.


## November 13 — MLPerf and CPSC raw-data reviews completed

Entries **46 (`mlperf_results`) and 47 (`cpsc_recalls`) are reviewed for their current raw-validation/metadata/SQL pipelines**. Corrected MLPerf original-host validation, exact result/file/tree matching, legacy CSV identities and CPSC original recall-row validation. Both sources are enabled under immutable contract 2.0.3; 70 old queued/failing jobs were superseded by new contract jobs with original evidence retained. **All 3,028 saved validation rows tested passed; 65 focused tests passed.**

Verified Athena snapshot: **451 MLPerf row occurrences and 262 CPSC row occurrences**, all raw-complete for their declared record kinds. MLPerf inventories and supporting files remain distinct from benchmark results. CPSC captured seven records today after the overnight network backoff recovered. Two old MLPerf batches remain excluded for missing commit evidence; full archive completion, historic availability, image downloads, rights and legal-entity matching are not certified.

All 15 historical executors, metadata lanes and enabled collection timers were checked. Repaired EODHD plan-manifest IAM access and successfully retried patent daily checkpoint contention. Other source validation holds and deliberate pauses remain; the previously deferred GitHub backup was not retried. No IAM edit or manual restart is required from you. [Review evidence](data-collection-processing/repair-notes/2026-11-13-mlperf-cpsc/review-complete.json) · [working SQL examples](data-collection-processing/repair-notes/2026-11-13-mlperf-cpsc/review-queries.sql).

## November 11 — NIH, NIST, awards, TED and patent pipelines reviewed

**No new API key, account or manual restart task for you for these seven configured routes.** Your metadata queries now return Athena data. Repaired original-response validators, the USPTO normalized assignment-ledger check, publication and credential placement. Verified fresh API capture, raw evidence and actual Athena payloads, including a NIST method PDF and TED notice XML.

Added bounded metadata continuation/publication and online database queue indexes after the sustained run exposed slow scheduling queries. Restored the older drained NIH historical route under the current scope. Daily/historical patent and assignment continuations use the existing authorised controller role. Approved USPTO document exclusions remain in force. **68 tests passed.**

Review scope matters: Google covers bibliography; full patent text remains a separate gap. USAspending covers selected contract-award summaries for named recipients; assignment histories cover eight applications. One older NIH batch lacks its original commit checkpoint and remains explicitly uncommitted, with raw files retained. Historical completion and every specialist feature are not certified. [Verified counts, exact scope and optional Athena samples](data-collection-processing/repair-notes/2026-11-11-grants-patents-procurement/README.md). This update supersedes older stopped-pipeline/access notes for these sources; unrelated source tasks remain below.

## November 11 — five FDA feeds repaired and reviewed

**No new FDA key/account/manual restart task for you.** Compliance actions, import refusals, inspection citations, Enforcement Report recalls and the industry-code reference now return Athena rows. Fixed FDA-specific original-response validation and replayed the failed inputs. All five sources are enabled with zero consecutive raw failures.

Fresh API capture, original evidence, metadata and native specialist Athena payloads passed for **442 records** across the five feeds. Verified metadata snapshot: **162 compliance actions, 425 import refusals, 195 citations, 179 recall observations and 217 industry-reference observations**; these are observations over capture dates. **66 tests passed.** Restored independent daily capture/publication; the PCB credential is used from its existing authorized controller role. Historical processing and metadata catchup continue.

Review scope is explicit: product codes currently cover **89 industry entries**; recalls retain the configured API columns and use modification-date selection. Original 483/warning-letter files, full product-code hierarchy, historical vintages and entity resolution are separate. [FDA evidence and optional Athena spot checks](data-collection-processing/repair-notes/2026-11-11-fda-authenticated/README.md).

## November 11 — CMS payments catalog and financial records reviewed

**No CMS access/key task for you.** The single catalog JSON contains dataset descriptions and repeated agency/contact information; individual payments live elsewhere. Repaired its stopped metadata validator. Your original catalog SQL now returns **168 raw-complete observations representing 40 dataset IDs**, including today's capture.

Actual Athena financial data verified: **76,013,225 Open Payments rows (15 editions)** in `optima_collected_data.cms_open_payments_rows` and **63,336 spending rows (5 editions)** in `optima_collected_data.cms_drug_spending_rows`. Full original fields are in `row_json`. Checked payment/ownership/spending payloads and automatically reconciled all 20 editions against committed CSV counts and original-file size/checksum receipts at **15:25 Madrid time**.

Restored daily discovery, resumable file collection, catalog metadata and Athena publication. Reused the preserved checkpoint and existing permissions; isolated CMS controller jobs in a capped 384 MiB budget after finding shared-memory throttling. **67 tests passed.** All 20 configured financial files are complete; earlier unconfigured releases and historical vintages are separate. Your optional next step is the [CMS financial Athena samples](data-collection-processing/repair-notes/2026-11-11-cms-payments/README.md).

## November 10 — CMS coverage policies and documents repaired and reviewed

**No new CMS key, account or manual restart task for you.** The SQL was correct; metadata processing had stopped because the generic JSON check rejected valid CMS responses. Added exact source-specific validation, replayed all eight original failed batches, and verified fresh API capture through both metadata and specialist Athena tables.

Verified metadata snapshot: **114 policy observations / 6 raw batches**, and **8 full-document observations / 8 raw batches**, all raw-complete, including November 10 captures. Original criteria and version fields are preserved; readable coverage text is available in metadata. Both sources enabled with zero consecutive raw failures. **61 tests passed.**

Independent CMS discovery, document capture and Athena publication timers are enabled. Daily refresh and annual historical/version discovery continue; successful capture enters the metadata queue directly. This is a functioning-pipeline review for national Medicare NCD data, not certification of a finished archive or all payer policies. Your optional next step is the [CMS Athena sample checks](data-collection-processing/repair-notes/2026-11-10-cms/README.md).

## November 10 — Crossref proceedings metadata repaired and reviewed

**No new Crossref access/key task for you.** Corrected a contract that wrongly demanded full papers from the configured metadata API. Athena now returns **321 raw-complete observations / 11 batches**. A fresh DOI lookup was verified in both metadata and conference curated tables, with matching DOI/title/publisher and complete returned metadata. Source enabled, zero consecutive raw failures. **43 focused tests passed.**

Restored bounded independent capture/publication timers and preserved old checkpoints. The large 2016-origin archive window advanced from 12,000 to **48,000 saved records** across real cursor continuations; it is still partial, and those counts are not all published. Daily capture is caught up through November 9. The old waiting controller jobs were replaced, with migration recorded in monitoring. Historical capture, metadata/publication catchup and full publisher papers remain separate from this metadata pipeline review.

**Your optional check:** run the SQL in the [Crossref repair report](data-collection-processing/repair-notes/2026-11-10-crossref/README.md). Crossref supplies DOI/proceedings metadata, including deposited abstracts where available; it does not supply the full papers. No manual restart is needed.

## November 10 — Europe PMC full text repaired and reviewed

**No new Europe PMC access/key task for you.** Fixed the missing official API-host mapping while retaining complete-article validation. Athena now returns **14 raw-complete observations / 14 batches**. Fresh current articles and a January 2021 historical article scope passed capture, metadata processing and publication. Readback in both metadata and specialist tables confirmed original XML plus matching titles and full article body text. **59 focused tests passed**; source enabled with zero consecutive raw failures.

Independent worker discovery/capture timers now continue two minutes after completion. Daily topic discovery and historical queue indexing are bounded; failed articles have their own cooldown and cannot stop other articles. Website-discovery receipts are kept as discovery evidence and no longer recur as missing full text. Twenty original article scopes were recovered into the queue. Historical completeness, remaining metadata/publication backlog, external supplements and historical-vintage coverage are still separate checks.

**Your optional check:** run the aggregate and random-row SQL in the [Europe PMC full-text repair report](data-collection-processing/repair-notes/2026-11-10-europe-pmc-fulltext/README.md). No manual restart is needed. Existing unrelated account/access tasks below remain applicable.

## November 10 — PubMed abstracts repaired and reviewed

**No new PubMed access/key task for you.** Fixed a metadata contract that incorrectly demanded full articles from an abstracts source. Original EFetch citations/abstracts now validate correctly. Athena returns **179 raw-complete observations / eight batches**, including **61 freshly captured daily-topic observations**. Titles, original citation XML and abstract sections were inspected in both metadata and specialist curated tables. Source enabled, zero consecutive raw failures; **52 focused tests passed**.

Restored an independent bounded worker daily job at **08:10 Europe/Madrid**, with hourly continuation and separate topic outcomes. The three configured topics cover vaccine, gene-therapy and immunotherapy clinical trials; this is not all PubMed or full article text. Historical jobs remain separate; their configured interval reports drained through October 26 with coverage not audited. Metadata backlog and archive/date-gap reconciliation are not declared complete. Other collection workers and metadata scheduling remain active; unrelated source failures still exist.

**Your optional check:** run the random-row SQL in the [PubMed repair report](data-collection-processing/repair-notes/2026-11-10-pubmed/README.md). No manual restart is needed.

## November 10 — NMPA trials repaired, resumed and reviewed

**No new NMPA key/account task for you.** Fixed dataset-specific metadata validation and verified **153 raw-complete observations** in Athena: 120 inventory rows, eight full trial snapshots and 25 events. Full detail payloads from both historical-pending and new 2026 trials are readable in metadata and regulatory tables. Inventory rows remain explicitly separate from full trial records. **79 tests passed.**

The substantive inventory/detail producers had been disabled during migration; they now run as bounded **worker** timers `optima-nmpa-resumed-inventory.timer` and `optima-nmpa-resumed-details.timer`. The existing 6,359 completed trials are preserved. Daily discovery, baseline continuation and detail processing have made real saved progress. Original controller timers remain disabled to avoid duplicates. Historical coverage and metadata/publication catchup remain in progress.

**Your optional check:** run the full-trial SQL in the [NMPA repair report](data-collection-processing/repair-notes/2026-11-10-nmpa-trials/README.md). No manual restart or new subscription is required based on the successful captures.

## November 10 — Chinese Clinical Trial Registry repaired and rechecked

**No new ChiCTR access task for you.** The fresh uncached Athena query now returns **94 raw-complete observations / 11 batches**, after publishing six further accepted batches. Metadata and regulatory payload checks show today's saved full trial detail with **73 fields**. Source enabled, zero consecutive raw failures. **55 focused tests passed on recheck.**

The remaining three website-discovery receipts were correctly classified as non-trial inputs, and their single open incident was resolved; files and audit history remain. Actual trial failures are still checked. Daily capture is scheduled for November 11 around **09:37 Europe/Madrid**. Its last run ended normally at the configured page budget, with partial catch-up windows still unfinished; that does not certify registry-wide historical coverage. Metadata processing and publication remain scheduled.

**Your optional check:** use **us-east-1 / AwsDataCatalog / optima-collected-data**, turn result reuse off, and run the SQL in the [ChiCTR recheck report](data-collection-processing/repair-notes/2026-11-10-chictr-recheck/README.md). No manual restart or new account is needed.

## November 10 — Health Canada NOC repaired and reviewed

**No access task for you.** The complete current official notice snapshot — **38,276 unique notices**, including inactive records and all five drug categories — is verified in curated Athena. The metadata query now returns fresh rows; the source is enabled with zero consecutive raw failures. Full-notice daily refresh runs at **07:55 Europe/Madrid**; historical date scopes continue. A separate bounded inventory adds every NOC product's brand name/DIN and linkage to its notice. **All 78,468 product records are also published and verified in Athena**, with zero missing notice links. Exact SQL, counts and evidence are in the [Canada repair report](data-collection-processing/repair-notes/2026-11-10-canada-noc/README.md).

**Your optional check:** open Athena in us-east-1, choose AwsDataCatalog / optima-collected-data, disable result reuse, and run the notice/product sample SQL in that report. This review covers NOC records; it does not establish all Canadian marketed-drug or historical-vintage coverage. Existing account/access tasks below remain applicable.

## November 10 — Japan PMDA feed repaired; owner action needed for all-drug access

**Today: register PMDA Medi-Navi and My Drug List.** You confirmed no account exists. The existing `japan_pmda` route only captures the public SAKIGAKE designation list. It does **not** meet the all-drug requirement. PMDA documents a separate all-prescription-drug package-insert download service behind that registration: [Medi-Navi](https://www.pmda.go.jp/safety/info-services/medi-navi/0006.html), [My Drug List registration](https://push.info.pmda.go.jp/mypage/view/mypage/agreementForUse.html), [official instructions](https://www.pmda.go.jp/safety/info-services/medi-navi/0012.html). Register, confirm the email, then choose the all-package-insert export (PDF and XML/SGML). Tell us when account/export access is ready; no password in chat. Bulk ingestion and daily bulk-update integration remain engineering work after access is available.

**Fixed now:** metadata host/validation failure and typed PDF-table parsing. Source contract 2.0.3 is enabled, zero consecutive failures. Requeued 34 jobs; replaced two incompatible legacy flattened extractions only after proving the corrected capture uses the same original PDF SHA-256 and covers every original record ID. Raw history and failure evidence are retained.

**Athena verified:** 50 raw-complete observations / two batches; today's full SAKIGAKE list has **25 records** and is published in curated regulatory Athena. Product, applicant and holder fields were checked. **39 focused tests passed.** Daily current-list capture is active at **07:45 Europe/Madrid**. All 15 standard workers and metadata processing were checked online; owner pauses elsewhere remain. Entry 21 is marked reviewed **for this existing designation scope only**. All-drug coverage remains explicitly pending. [Repair and account steps](data-collection-processing/repair-notes/2026-11-10-pmda/README.md).

## November 10 — UK MHRA reviewed; broader medicine-document capture running

Repaired `uk_mhra` metadata validation: official register attachments were saved but the old empty host contract/generic validator rejected them. New contract 2.0.3 validates original CSV/XLSX rows and separately validates linked medicine PDFs plus their exact official catalogue evidence. Source enabled, zero consecutive failures; 51 unfinished old-version jobs requeued.

**Athena verified:** 70 raw-complete observations / four batches, including today's new product document. Original PDF and **29,641 characters of extracted text** verified in both metadata and curated regulatory tables. Entry 20 is reviewed and its SQL uses `uk_mhra` (separate from `japan_pmda`). **43 focused tests passed.**

**All-drug scope widened:** existing ILAP/orphan lists alone were too narrow. `optima-mhra-products.timer` now traverses the whole public product-information catalogue without company/product/document-type filters, saving original PDFs and extracted text. It continues every two minutes with 384 MiB/20% CPU and up to ten entries/run; document failures/timeouts are separate gaps and do not stop subsequent documents. Initial catalogue count 79,646, later 79,648: these are document entries, not unique drugs or all-current-licence proof. First ten documents completed without failure; remaining download and metadata/publication backlog continues. Index-only evidence cannot pass as a complete medicine document.

All 15 standard workers and metadata/capture/publication schedules were checked online. No owner key/account action is needed. Complete catalogue coverage, current authorisation status, historical vintages, undated designation history and OCR of image-only PDFs are not certified. [Evidence and full-text inspection SQL](data-collection-processing/repair-notes/2026-11-10-mhra/README.md).

**Separate monitoring repair discovered:** `constellation-gap-audit.service` OOM-kills at its 512 MiB cap; its SQL is batched but its Python code retains the entire job/receipt inventory. Stream/reduce the coverage inputs and bound caches, then verify a successful audit. Its timer remains active, but the audit is stale until repaired. Capture and metadata continue. No owner credential action is required for this software repair.

## November 10 — EMA medicines reviewed; complete current report verified in Athena

Repaired `ema_medicines` metadata validation using official report origin, EMA product ID and exact original-row equality. Source contract 2.0.3 is enabled with zero consecutive failures; 40 unfinished jobs requeued. **Metadata query now returns 160 validated observations / five batches**, including today's capture. Source data is broader than the current labelling subset: **all 2,757 current report rows are published and verified in curated Athena**, with **2,357 human / 400 veterinary** medicines and all reported statuses retained.

New independent worker timer **optima-ema-medicines-daily.timer** captures the full current report daily at **07:35 Europe/Madrid**, with boot catch-up and 384 MiB/20% CPU bounds. No company, category or authorisation-status filter. Count/distinct-product reconciliation in Athena exactly matched provider totals. Daily shared execution skips the dedicated EMA lane; existing historical date scopes continue. Those are current report rows with historical first-publication dates, not recovered historical vintages.

Entry 19 is reviewed and its SQL explicitly uses `ema_medicines` / AwsDataCatalog. All 15 standard workers, metadata processing and capture/publication schedules were checked online; source holds elsewhere remain. **43 focused tests passed.** No credential action is needed. Scope is the EMA published report, not every national European medicine or all linked EPAR PDFs. [Evidence and full-snapshot query](data-collection-processing/repair-notes/2026-11-10-ema-medicines/README.md).

## November 10 — Drugs@FDA applications reviewed; all-provider inventory running

Repaired `drugsfda_applications` metadata validation against entire original FDA application results, including every returned product and submission. Requeued 20 unfinished old-contract jobs; reviewed-source contract 2.0.3 is enabled with zero consecutive failures. **Athena: 192 raw-complete observations / five raw batches**, including new November 10 inventory capture. Both metadata product-array readback and curated specialist application queries passed. Entry 18 is now reviewed; it uses `drugsfda_applications`, separately from openFDA event records and EMA medicines.

**All-drug coverage:** existing historical/daily date queries have no company filter, but cannot alone cover older applications with no recent activity. Added a separate weekly all-provider inventory, split into 30 numeric application ranges plus an unexpected-ID complement. Live API reported **29,447 applications**. Retains all returned products, including discontinued drugs. New `optima-drugsfda-inventory.timer` continues every two minutes on the worker, capped at two scopes/four pages per scope, 384 MiB and 20% CPU. Initial saved checkpoint committed 800 applications; remaining partitions/pages continue. No finished-inventory or all-world-medicines claim is made.

All 15 workers and metadata/capture/publication schedules were checked online. **34 focused tests passed.** No owner credential action is required; rerun entry 18's SQL in us-east-1 / AwsDataCatalog / optima-collected-data with reuse off. Existing other-source validation holds and Constellation product-entity discovery remain separate. [Detailed evidence and scope](data-collection-processing/repair-notes/2026-11-10-drugsfda/README.md).

## November 10 — openFDA query rechecked

openFDA remains reviewed and enabled, with zero consecutive metadata failures. Published two newly accepted batches; final query `214f3440-5582-4180-9ef6-660f1bc741f1` returned **108 raw-complete observations / seven raw batches**. Before that publication, a fresh, uncached query explicitly using `AwsDataCatalog` returned **75 observations / five raw batches**; query ID `33f10377-35d6-43af-bfff-66d1318d843a`. Both metadata and curated provider-payload queries also returned records. The console's empty result was not reproduced. Entry 17 now specifies **account 059416028963, us-east-1, AwsDataCatalog, optima-collected-data**, with result reuse off. If still empty, compare the failing execution ID with the successful one; no console-context cause has yet been established.

All 15 workers, metadata processing and capture/publication schedules were checked online. Owner pauses remain. Existing raw-validation holds and capture catch-up remain separate; latest checked nonempty openFDA ingestion is October 31. [Current checks and console steps](data-collection-processing/repair-notes/2026-11-10-openfda-recheck/README.md).

## November 10 — product-search database error repaired; discovery dependency remains

**Affected collector:** `optima-product-search-daily.service` (S65 / DataForSEO product search attention), separate from CTIS. It still queried the deliberately retired `tracking` schema. Connected it to **all named product entities in Constellation's `metadata_engine` registry**, including provisional candidates, with no manual watchlist or inferred ownership/sector.

The actual service now completes successfully and its timer remains active. **12 tests passed.** Empty-registry checks avoid paid calls and shared capture locks, and save an explicit pending-dependency status to S3. Existing provider budgets and supervised collection resume automatically when product entities appear.

**Remaining engineering work:** Constellation currently has **zero product entities**; its graph extraction does not yet create them from captured product evidence. Implement source-supported product discovery/entity/name registration, then verify paid capture, raw commits and Athena publication. This is not fixed by recreating `tracking`, changing an API key or choosing a manual subset. Product capture remains pending, not complete; no new product observations were claimed. [Repair and live evidence](data-collection-processing/repair-notes/2026-11-10-product-search/README.md).

## November 10 — openFDA repaired and reviewed

Fixed the empty metadata SQL: the old contract had no allowed provider hosts, so valid saved API responses were rejected. Deployed exact application/submission/CRL identity checks under contract 2.0.3, requeued 21 unfinished old-contract jobs and successfully replayed five batches. The source is enabled with zero consecutive failures; reviewed-source date queues keep individual gaps separate. **39 tests passed.**

**Athena:** 75 raw-complete observations / five linked raw batches; application IDs, approval status and full provider payloads verified. Published and read back a 14-record complete October 23 regulatory window. Both live openFDA approval and CRL endpoints passed authenticated probes November 10. API responses and validation evidence are saved. No new key or owner access action is needed; rerun entry 17's SQL.

**Freshness remains catch-up work:** the newest checked nonempty raw batch was ingested October 31. The shared collector successfully completed an empty October 24 calendar window November 9 and advanced its catch-up cursor to October 25; active capture schedules continue. This review does not mean history is finished or that current-day data has caught up. All 15 workers and metadata/publication timers were checked active; separate source holds and the previously documented product-search directory/database failure remain. [Evidence and exact Athena checks](data-collection-processing/repair-notes/2026-11-10-openfda/README.md).

## November 10 — CTIS reviewed and processing resumed

EMA CTIS now uses validated API trial details and matched application/decision events under immutable contract 2.0.3. The metadata source is **enabled**, zero consecutive failures; public discovery pages remain separately recorded gaps and cannot stop this reviewed source. Requeued 65 unfinished jobs; two bounded batches passed strict original-response validation and replay. Athena metadata query returned **1,996 raw-complete observations / 84 raw batches**, latest capture November 9. Published **35 trial/event records** in two complete curated windows (November 6 and 8); readback and payload evidence are in the [repair report](data-collection-processing/repair-notes/2026-11-10-ctis/README.md). Marked entry 16 reviewed in the raw verification schedule. **34 tests passed.** No CTIS API key or owner access step is required; rerun the supplied SQL to inspect the data.

Daily/historical controls permit work. All **15 workers** are active; the metadata worker processed eight jobs successfully, metadata controller succeeded in its isolated slice, and collection/publication timers are active. Owner pauses are preserved. Other sources still have raw-validation holds; this is not an all-source completeness certificate.

**Separate engineering issue found today:** `optima-product-search-daily.service` failed because its directory query targets the nonexistent RDS `tracking` database (`Unknown database 'tracking'`). Its retry timer is enabled. Reconcile the intended directory database/schema and connection before replaying this collector; do not create an empty replacement database and call it repaired. The unrelated code-backup service also remains failed. Neither issue blocks CTIS or metadata processing.

## ClinicalTrials.gov repaired and reviewed — November 9

**The previously empty metadata SQL now returns 128 validated observations across four raw batches, including November 9 capture.** Fixed its empty provider-host contract with exact NCT/provider-response validation, replayed failed batches and verified publication in Athena. Contract 2.0.3 is enabled with zero consecutive failures and non-blocking reviewed-source date queues; 33 old-version jobs were superseded/requeued without deleting raw data. **41 focused tests passed.** No API key or account action is required from you; rerun the existing review query.

Full study protocol data is available in `optima_metadata_engine.source_observations.labelled_json` under `$.payload.data`, with NCT ID, sponsor, status, interventions, outcomes and supplied provider fields. ClinicalTrials.gov captures current study versions, not past-vintage snapshots. The older curated regulatory window table was also payload-checked, but its latest checked observation is October 15. The newest captured window is partial (300 records); finishing capture and curated publication remains engineering catch-up, not a completed historical archive.

**Runtime check:** daily and historical controls permit collection. The metadata controller had been timing out behind a memory-heavy EDINET process; moved it to its own 256 MiB sibling slice and verified subsequent successful discovery/publication cycles. Worker processing and publication are progressing. Other sources still have **74 raw-validation holds** and five owner pauses; engine availability does not make those sources complete. The separate code-backup service remains failed and is outside collection/metadata. [Evidence and exact Athena checks](data-collection-processing/repair-notes/2026-11-09-clinicaltrials/README.md).

Reviewed the November 9 email, current receipts/journals and targeted live probes. The catalog and SQL links below retain their dated baseline; a successful sample does not certify full history or original raw-content completeness.

## Personnel announcement archives repaired and reviewed — November 9

The empty `personnel_archive` metadata query was caused by validating a derived archive wrapper as a standalone provider record. Added committed-parent observation/record/URL linkage, pinned manifest/batch checks and upstream original-content validation under immutable contract `2.0.3`. Individual missing/unsupported parent bodies are recorded separately; valid records continue. Personnel/event/entity classification remains unverified.

**Athena now returns nine raw-complete archive observations / five raw batches**, including a fresh November 9 capture from repaired RSS input. Curated payload inspection verified the nested **1,958-character** article body and S3 evidence reference. **37 focused tests passed.** Marked Personnel announcement archives reviewed; preserved old failed reports and requeued old-contract inputs. No new owner key or access step is needed.

**Runtime check:** daily/historical controls enabled; all **15 historical workers** active; metadata worker/controller schedules enabled with fresh accepted jobs. No failed data worker units remained after clearing only recovered diagnostic flags; the controller's separate code-backup unit is still failed. Owner pauses are unchanged. **75 other sources retain raw-validation holds**, and **2,137 accepted metadata batches await publication** at this snapshot. Infrastructure being online does not certify every source or complete history.

The IDE-selected query for `clinicaltrials_gov` is a different source and remains a separate validation repair. Its review checkbox has not been changed. Use the updated Personnel archive query (`source_key='personnel_archive'`) for this review. [Evidence](data-collection-processing/repair-notes/2026-11-09-personnel-archive/README.md).

## People RSS article bodies repaired and reviewed — November 9

Implemented **explicit RSS full content → direct publisher article → Decodo fallback**. Existing descriptions/URLs do not establish full-text completeness. Original HTML/feed bytes, extracted text, checksums, chunks and direct/rendered provenance are retained. Explicit access restrictions are not bypassed; unavailable bodies and rate limits stay as gaps.

Repaired metadata with immutable contract `2.0.3` and original-body verification. Valid articles continue while unavailable ones enter a durable per-article failure queue. Old failed reports remain; 136 old-contract jobs were superseded/requeued. The metadata query now verifies **42 full-text observations / five raw batches**. Curated Athena payload inspection verifies the corrected **2,939-character** article and its S3 evidence reference. A live budgeted Decodo probe independently extracted **2,945 characters**.

The independent worker `optima-rss-content-repair.timer` is enabled on the historical worker and retries up to two saved article gaps every two minutes under a 512 MiB/25% CPU cap. A successful production run captured additional BioSpace and Energy Storage News bodies (**1,958 / 3,018 characters**) and queued their corrected observations for metadata. Existing feed collection and research publication schedules remain enabled. Decodo uses a 40-request RSS daily cap plus existing shared provider controls; direct publisher budgets remain bounded.

Marked RSS **reviewed** after **40 focused tests**, actual article capture, metadata/Athena publication and curated text checks. This does not mark all linked articles or saved history complete. No new key/account step is required; remaining body gaps and publication catch-up are engineering work. [Evidence](data-collection-processing/repair-notes/2026-11-09-people-rss/README.md).

## Finlight repaired and reviewed — November 9

Finlight's empty metadata query was a real validation blockage: the contract had no allowed API hosts, and generic substantive-content rules could not verify its news response. Deployed a source-specific validator and immutable contract `2.0.3`; API request receipts cannot pass, and article identity/provider fields must match the original checksummed response. Publisher full text remains separate from news-provider record completeness.

**Verified in Athena:** metadata query now returns **160 raw-complete observations / five raw batches**, including November 9 capture. Curated news now has **13,740 distinct Finlight articles** with November 9 ingestion after publishing a complete November 3 query set (all eight sector/language manifests). Finlight is marked reviewed and uses non-blocking source/date failure queues. Both news capture/publication timers remain enabled; remaining metadata jobs continue processing.

Corrected the finite archive's unsupported 2016 cursor to its verified **January 2021** start; pre-2021 availability remains unverified, not permanently excluded. Enabled and queued the isolated historical route. Repaired its executor registry and worker credential wiring; the historical workspace uses the existing `dataSourceAPIkeys` bundle's mirrored `finlight-api-key` field, with other fields unchanged. Existing 1,000/day and 100/invocation request limits remain. No new API key or subscription purchase is needed.

The repaired historical invocation is **running**, resuming the retained **November 10, 2021** checkpoint. Actual API/publisher budgets and full-text cache writes advanced at 16:37 UTC after repairing the cache/budget prefix permissions. Existing limits remain; publisher pages that cannot supply full text retain explicit unavailable/pending status.

Historical completion, all publisher full text and the Pro downgrade notice are not certified by these samples. Existing receipt-based completion checks remain. [Implementation, verification and live archive state](data-collection-processing/repair-notes/2026-11-09-finlight/README.md).

## Disclosure Documents and Candidates restarted — November 9

**Fresh capture-to-Athena verification passed.** Documents now have **538 rows / 288 distinct record IDs**; candidates have **926 rows**. Both show November 9 ingestion. Repaired October 16 capture produced five documents and five passage-supported candidates, all published through verified canonical windows. Licensing-agreement candidates were correctly zero for that day; their last nonempty observation remains older.

Moved disclosure capture from the controller shared queue to isolated worker services with **512 MiB memory / 25% CPU** limits and one disclosure invocation at a time. Daily timer resumes after 120 seconds; historical timer after 300 seconds. One source-calendar day per invocation, with resumable record/page limits. Preserved the daily cursor, verified its advance to **October 17, 2026**, and enabled historical capture from **January 1, 2016 through October 14, 2026**; its first complete-day receipt advanced to **January 2, 2016**. Daily capture covers October 15 onward and then follows newly completed days.

Applied narrowly scoped worker checkpoint read/write permissions. Disabled the superseded controller S11 daily timer and removed it from the controller resume list to avoid duplicate execution. Existing research-publication scheduling continues to discover and publish committed windows; five repaired derived windows were published and counted in Athena during this repair.

**No owner access action is needed.** Remaining work is backlog processing and continued publication verification, not a completed historical-data claim. The first repaired day retains one unsupported embedded-file gap and unresolved company identities; candidate events remain unreviewed. [Deployment, receipts and Athena evidence](data-collection-processing/repair-notes/2026-11-09-disclosure-resume/README.md).

## EDINET reviewed — live check November 9, approximately 17:00 CET

**Owner review complete for `edinet_filings`. No new key, purchase or account step is needed.** Applied reviewed-source/date queue handling locally, on the metadata worker and in runtime installation defaults. Individual failures remain recorded without stopping the entire EDINET source.

Repaired seven metadata retries: the validator was attempting to load derived extraction JSON (one was 61 MB) as original-provider evidence. EDINET now retains extraction links and validates original PDF/ZIP evidence instead. Derived JSON alone cannot satisfy original-document requirements. All seven jobs committed successfully; published 18 previously accepted EDINET batches through bounded staging/count checks. Athena now verifies **138 raw-complete observations / 138 linked raw objects**, query `bccb8a46-4dde-4ccd-b387-3585319bc50e`. Latest published ingestion is **November 1**; this does not certify current-day freshness or full history.

**Infrastructure functioning:** daily/historical controls enabled; all 15 historical workers active; metadata controller and worker show fresh successful jobs; scheduled research publication completed verified releases. No collection/metadata systemd unit was failed. The separate code-backup service remains failed.

**Outstanding engineering work, highest attention first:**

1. **78 source-specific raw-validation holds** remain. Their missing original artifacts/contracts must be repaired; collection of other sources continues. Owner pauses are retained.
2. **Metadata publication catch-up:** approximately 2,000 other accepted batches remain pending. EDINET’s accepted backlog at the start of this check was published, but thousands of its input jobs remain queued. Processing an old input now does not change its original ingestion timestamp.
3. Latest saved health report (15:30 UTC, no inspection errors) retains **collection prerequisite incomplete**, **market coverage gaps (175 daily / 202 historical symbols; 52 reviewed exclusions)**, and **patent PDF unavailable/source refresh required**. These require scoped investigation; this check does not close them or waive evidence requirements.
4. **Disclosure freshness** was repaired later November 9; the newest section above supersedes this earlier October 21 baseline. Full historical catch-up remains pending.

[EDINET review, repair and runtime evidence](data-collection-processing/repair-notes/2026-11-09-edinet-review/README.md).

## What you need to do today — Monday, November 9

**No source-access action is required from you for the current USPTO document gap.** On November 9 you instructed us to skip **MMOWZII4X158X88** in application **35526479**. That exact exception is now configured and tested; the earlier support request is withdrawn. Other documents in the application still require normal capture. The original failed receipt and denial evidence remain archived, and the record explicitly states that the PDF was excluded rather than captured.

Your BLS permission approval has also been applied and verified. Census activation, Copernicus terms and SMS setup do not need repeating. No new purchase or API key is requested by these checks.

Optional: continue the [SEC](#q005), [FDA enforcement](#q036) and [EIA](#q055) Athena payload checks. Return query IDs and example records for missing fields. The remaining infrastructure repairs below are implementation work.

## HKEX repaired and collection resumed — November 9, 16:49 CET

**No new key, purchase or account action is needed for this HKEX repair.** English availability notices were being mistaken for original announcements. The collector now archives same-issuer/same-minute Chinese candidates under their own HKEX IDs, retaining their listing/PDF evidence and recording that translation equivalence is unverified. The notices remain separate from substantive filings.

All four failed HKEX metadata batches were replayed successfully and published through staged Athena count verification. Actual Athena queries returned **86 raw-complete row occurrences / 53 distinct filing IDs**, with Chinese payload/PDF provenance inspected and zero English placeholder IDs counted as filings. Query: `063ba399-87f9-4036-a6f1-0f73b3922f4a`. The four batches overlap; 86 is not a unique-document count or a full-history claim.

Restored **33 existing daily capture/publication timers**. Daily and historical collection controls are enabled; all **15 historical workers** are running; metadata worker/controller timers are active, with fresh accepted jobs after deployment. Reddit, Bluesky, GitHub and Marketaux remain owner-paused; access-layer exclusions remain unchanged.

**Remaining engineering work:** metadata processing is enabled for 70 sources; **78 other sources still have raw-validation holds**, plus 5 owner-paused and 4 access-layer entries. Those holds were not waived. The general metadata publication queue still has **2,066 accepted batches awaiting publication** at this check; HKEX's four repaired batches were published directly and verified. Historical completion, later HKEX batches, downstream disclosure dependencies and publication throughput still require tracking. This resumes infrastructure and repairs HKEX; it does not certify every source pipeline as healthy.

**Your next step:** rerun the HKEX query in [RAW_DATA_VERIFICATION_SCHEDULE.md](data-collection-processing/RAW_DATA_VERIFICATION_SCHEDULE.md), then inspect sample `labelled_json` payloads and original-document links. Mark HKEX reviewed only after your content check. [Implementation, evidence and sample SQL](data-collection-processing/repair-notes/2026-11-09-hkex-repair/README.md).

## Latest runtime check — November 9, approximately 16:15 CET

SEC company financial facts is recorded as owner-reviewed. Its source is enabled and uses the same source/date error queue as the other reviewed sources. Athena verified **8,439 raw-complete observations linked to 198 raw objects**. The published sample's latest ingestion date is October 26; metadata processing/publication is still catching up.

Repaired S11's missing shared-runtime startup wrapper, restored eight overdue enabled daily services, restored the company-catalogue timer and corrected the daily runner's expected partial-exit handling. Remote historical workers and the metadata engine show fresh processing. The public archive/raw services completed new runs. Queued services still need their post-repair completion checks.

Metadata infrastructure is running, while **79 sources remain raw-stopped**, 5 owner-paused and 4 access-layer entries. Those raw-content holds remain explicit; this is not a claim that every source is healthy. No new owner action is required beyond the reviews already in progress. [Detailed runtime check](data-collection-processing/repair-notes/2026-11-09-runtime-check/README.md).

## Repairs and verification completed November 9

| Item | Result | Remaining verification |
|---|---|---|
| USPTO document exception | Exact document `MMOWZII4X158X88` excluded by owner; live saved-record verification passed with zero provider requests. Original failure archived. | Normal window catch-up/publication must still be verified; no PDF coverage claimed. |
| HKEX changing index | Saved complete daily index before downloading documents; checksum/provenance checked on resume. September 23 live test returned **890 entries**, explicitly exhausted. Deployed; normal daily run started. | Finish linked-document capture, dependent disclosures and Athena publication. Index success alone is insufficient. |
| Zenodo dates | Valid dates with trailing whitespace now normalize correctly. Original dates and intervals remain in raw payload; ambiguous dates carry explicit unknown status. Deployed; normal retries retain the existing provider HTTP 500 cooldown. | Verify actual repaired-date commits and publication after the cooldown. |
| BLS worker S3 access | Applied your approved narrow permission repair. Actual worker read/write checks passed in all **three metadata folders**. Six old permission-failed scopes now have **complete, exhausted manifests covering 70 observations**. | Verify these exact BLS batches in Athena; no full-source history claim. |
| USDA publication | Exact repaired cotton batch is **verified in Athena: 1,500 rows / 1,500 distinct IDs**, matching its S3 manifest. Query `36c69eb3-dbe4-4eb8-9f67-85d27063a0d7`. | Other USDA commodities/years remain separate scopes. |
| Tests / deployment | **46 targeted tests passed**; four modules deployed to 149 historical workspace roots plus controller/daily copies. | Live completion is reported separately above. |

## Current engineering work — highest priority first

| Priority | Remaining issue | Required next step |
|---|---|---|
| 1 | HKEX original documents and dependent disclosures | Exercise the saved-index collector through committed document batches; verify downstream manifests and Athena. |
| 2 | BLS / Zenodo repair verification and publication queues | Inspect exact replay results; retain provider cooldowns and resource locks; verify committed output and Athena readback. |
| 3 | USPTO office-action document gap | Apply the owner-approved exact-document exclusion, then verify subsequent committed pages and publication. No account-owner support task remains for this document. Other document failures remain separate. |
| 4 | Historical source gaps | Continue scoped repairs for FDA, preprints, EDINET, FRED, DataCite, Census, Copernicus, ClinicalTrials, MHRA/CTIS, WTO, USGS, TED and USAspending. TED's old S3 denial needs exact-key diagnosis before another permission change. |
| 5 | Market coverage | Email baseline: **175 daily and 202 historical unresolved symbols**, with **52 reviewed exclusions**. Review exact ticker/date evidence; no blanket exclusions. |

The November 8 database index repair remains applied; repaired routes dispatch quickly and workers execute. The email's **236 gaps longer than five days** include older failed scopes. The separate 3,933-failure handoff is older evidence. These counts do not mean that every source failed again today. HTTP errors alone do not justify permanent exclusions.

[November 9 repair evidence and limitations](data-collection-processing/repair-notes/2026-11-09-checkup/README.md).

## Earlier November 5 repair record


- **Email delivery:** the oversized-subject fix is deployed; you received the email, current notification errors are empty and CloudWatch reports OK. The emailed HIGH entry was the pre-recovery state, not a fresh capture failure.
- **Search monitoring:** corrected the nonexistent `optima-search-daily.timer` reference to the enabled weekly `optima-search-capture.timer`; aligned grace with its weekly schedule. A service not yet invoked since boot uses timer activation for schedule grace, never as proof of collected data. Next observed trigger: **Friday November 6, approximately 11:01 CET**.
- **Conference monitoring:** the daily checkpoint is caught up to November 5 with an exhausted committed manifest. Removed the migrated historical checkpoint from this daily service's scope. Verified current-scope completion can now resolve an old stall without fabricating new rows. Historical conference work remains tracked separately.
- **HKEX recovery:** changed-prefix/changed-total failures previously kept resuming an invalid cursor. The runner now starts a fresh immutable run after six hours, preserving older evidence and dependent-source gates. Tested and deployed to the controller and historical workspaces; successful live recollection and downstream Athena publication are **not yet verified**.
- **USGS historical archive URLs:** added 19 exact links discovered on official USGS mineral pages (2015–2019, including prior-edition comparisons). Four 2016 reports downloaded and parsed: lithium 67, cobalt 105, nickel 128, graphite 88 statistics. Lithium and graphite retain parsing/unit review flags. These are probe results, not newly published Athena counts. Deployed to daily and historical collectors; remaining failed-scope replay and publication are still open.
- **Tests:** 83 focused tests passed. A broader run also exposed an existing missing `company-universe.v0.2.json` fixture target; that separate test was not counted as passing.

[Repair evidence, deployments and limitations](data-collection-processing/repair-notes/2026-11-05-email/README.md).

## Email items still open — engineering work, not additional account tasks

These November 5 findings are retained as dated engineering detail; the November 7 section above supersedes account actions and counts.

| Priority | Unresolved items | Required repair / verification |
|---|---|---|
| 1 | Shared-lock waits: authenticated capture, committed Athena, daily audit, patent global/prosecution/publication, people and specialist publication | Bound long-running batches and verify queued services get execution time within the host memory budget. Do not remove locks or run competing publishers to silence alerts. Latest email waits were 48–237 minutes; invocation/progress alone does not establish full publication. |
| 2 | HKEX and dependent documents/disclosures | Verify a post-deployment changed-index refresh succeeds, then require matching upstream manifests before dependent capture. |
| 3 | Census and Copernicus historical scopes | Reconcile old access failures against working credentials; verify resumed production jobs and Athena publication. Copernicus still needs structured weather extraction beyond raw NetCDF. No owner access work remains. |
| 4 | USGS; TED; BLS | Replay repaired USGS archive scopes, retain extraction gaps and publish verified output. Investigate TED/BLS exact failed artifact permissions, requests and checkpoints before any narrowly scoped permission request. The earlier approved USGS metadata permission repair remains complete. |
| 5 | FDA, ClinicalTrials, MHRA, EMA, EDINET and OpenDART | Replay date/identity/request failures; inspect provider responses and archive retention. Do not classify HTTP failures or old windows as permanently unavailable without evidence. |
| 6 | Patents, bioRxiv/medRxiv, DataCite, Zenodo, Europe PMC; NSF/arXiv in the old handoff | Repair duplicate identities and unstable pagination without discarding distinct versions; retain rate limits and bounded retries. Earlier successful probes do not close every failed scope. |
| 7 | FRED, WTO, USAspending and USDA | Reconcile fixed request scopes and replay remaining failures. Keep explicit unavailable-vintage evidence distinct from request defects; USDA route/authentication repaired November 7; production replay and publication remain to verify. |
| 8 | Market coverage | Review the email's 182 daily and 202 historical unresolved symbols; 52 scoped exclusions already exist. Validate mappings, trading dates and provider evidence before excluding more windows. |

The email contains **55 historical scope groups**, not 55 wholly failed sources. Its **3,933-failure handoff is dated October 30**. No blanket closure, raw-artifact waiver or permanent exclusion was applied. The separate stopped-raw-jobs checklist remains open where original documents/exports are required.

## Repairs completed or checked November 4

- **Census and Copernicus access resolved after activation/acceptance:** the 12:51 UTC Census probe returned **36 February 2016 trade rows**. Both ERA5 single-levels and ERA5-Land sample retrieval jobs completed successfully; their 25 KB downloads passed size and file-signature checks. These local samples are not production Athena records. Your account tasks are complete. Daily source configuration remains enabled under the running shared daily timer. Historical queue inspection timed out; resumption of parked scopes and production Athena publication remain engineering verification, not confirmed recovery.

- **Monitoring index read repaired:** the runtime index had grown to 21,563,527 bytes, beyond the old 8 MiB metadata cap. Only that named index now has a bounded 32 MiB cap; ordinary metadata retains its 8 MiB limit. Its 51,713 paths loaded successfully.
- **Live health refresh:** all **29 jobs inspected with zero inspection errors**. The refresh still recorded **19 active service alerts**; this is not an all-clear for their collection work.
- **Overview corrected and deployed:** service counts now exclude historical-scope labels; historical scopes are shown separately. The reported **3,933 historical failures** came from a handoff dated **October 30**, not a fresh November 3 recount. The report now exposes that evidence timestamp. Historical-scope guidance points to receipts/checkpoints rather than nonexistent systemd units.
- **NSF targeted replay:** the February 29, 2016 query returned **53 unique records across three pages**, exhausting pagination without the earlier duplicate failure. One retry of that exact parked scope was authorized in the queue; latest observed status is **pending**, attempts **2**. No committed recovery or Athena publication is claimed yet.
- **Validation:** 22 focused tests passed. Monitoring Lambda deployment completed successfully. No test SMS/email was sent.

[November 4 repair evidence and remaining limitations](data-collection-processing/repair-notes/2026-11-04-checkup/README.md).

## Collection failure policy

A failed source/window is logged and deferred; independent sources must continue. Failed work remains incomplete and visible for repair. October 28 changes isolate publication discovery and source-group exceptions, increase repeated-failure cooldowns, and prioritize lower-attempt historical jobs. Existing concurrency limits and three-attempt parking prevent one failed job from occupying the pool indefinitely. [Implementation, tests and deployment receipts](data-collection-processing/repair-notes/2026-10-28-isolation/README.md).

## Earlier repair detail — October 30 (superseded by November 4 priorities)

| Priority | Source / pipeline | Current finding | Next action | Owner |
|---|---|---|---|---|
| 1 | **118 US Census trade** | Live authenticated request returned HTTP 302 to `/data/invalid_key.html`. This is rejected access, not unavailable historical data. Collector now reports `census_api_key_rejected`. | Sign into/check the Census API-key registration email; confirm activation, then replace only `US-census` in the existing `dataSourceAPIkeys` secret with the issued key. Do not paste it into chat. Tell me when updated so the same bounded query can be retested. No paid plan requested. | You, then engineering |
| 2 | **042 TED; 050 USGS** | Historical AccessDenied/download failures remain in the supplied checkup. A 404 or permission error does not prove the underlying data does not exist. | Obtain the exact denied artifact key, correct the narrow worker permission or official archive URL, replay the failed scope, then verify publication. No blanket exclusion. | Engineering |
| 3 | **017 FDA openFDA** | Alerts still contain earlier invalid-date, duplicate-ID and HTTP 400 failures. October 28 parser fixes do not prove those earlier scopes have been repaired. Undated submissions are retained as unknown dates, not discarded. | Replay the earlier failed windows using the deployed parser; inspect remaining HTTP 400 bodies; reconcile successful checkpoints into gap reporting and verify Athena output. | Engineering |
| 4 | **147 Zenodo; 143 DataCite; 145 bioRxiv / post-launch medRxiv** | Request errors, oversized responses, duplicate identities and pagination remain repairable/unresolved. Only pre-launch medRxiv windows qualify for the reviewed exclusion below. | Replay exact failing query scopes, repair request/identity logic and split oversized scopes. Preserve partial commits and avoid retry loops. | Engineering |
| 5 | **075 ERA5; 066 FRED; 125 USDA; 071 WTO; 098 OpenDART** | Access/provider/request failures remain unresolved. Existing keys do not prove dataset entitlement; HTTP errors do not establish missing historical data. | Validate exact response bodies and parameters before asking for replacement credentials. For a demonstrated entitlement denial, provide the specific dataset/account action. | Engineering first |
| 6 | **EMA, Europe PMC, USAspending** | Interruptions, source changes and exhausted retries remain in the supplied checkup. | Resume bounded scopes, validate pagination/counts and retain failures for targeted repair. Do not label these permanent gaps. | Engineering |
| 7 | **Publication / NMPA / other repaired captures** | Earlier timestamp and capture fixes still require final publication evidence for their repaired windows. | Query the matching Athena windows and inspect payloads; successful capture or local curation is not sufficient. | Engineering; your random SQL checks afterward |

## Reviewed unavailable data — retained, not an action item

**145 medRxiv before June 2019:** the provider confirms a June 2019 launch ([CSHL evidence](https://www.cshl.edu/cshl-and-plos-partner-to-host-papers-on-medrxiv/)). The reviewed rule excludes only medRxiv windows wholly within `[2016-01-01, 2019-06-01)`. June 2019 and later remain eligible; bioRxiv is unaffected. The collector records `accepted_unavailable` with a durable decision receipt instead of calling the provider or claiming complete coverage. Gap reporting retains these in a separate accepted-unavailable list and omits their recurring repair alerts. This is the only new permanent exclusion established in this review.

**071 WTO HTTP 204:** repaired as an empty query response, not a permanent data exclusion. The 2016 `ITS_CS_AM5` replay completed with zero records and a committed manifest. A 204 after pagination has already started still fails validation. Other WTO failures remain open; historical alert reconciliation/publication is separate.

**Monitoring repair:** the gap reporter's unbounded database history read timed out. It now reads in 500-job keyset batches. The live refresh succeeded on October 30 at 12:07 Madrid: 41 accepted-unavailable windows, 139 flagged merged intervals and 51 record-only intervals. These counts describe intervals, not source counts. See [October 30 repair evidence](data-collection-processing/repair-notes/2026-10-30-gaps/README.md).

**SMS:** owner confirmed delivery; remains removed from action items. Marketaux, GitHub, Reddit, Bluesky and NICE pauses remain unchanged. All older counts and Athena previews below retain their original audit date.

## Longer-term access backlog — not required for today’s repairs

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
| 051 UN Comtrade | `UN-primary / UN-Secondary (register spelling); deployed presence check found UN-secondary` | Verified 13 November: current keyed annual capture archived native rows through today and passed exact original-response validation; Athena publication repaired. No new key or credential edit needed for this scope. |
| 066 FRED / ALFRED series and vintages | `FRED` | October 26 probe succeeded; October 28 checkup now includes historical request failures. Repair the failing scope and verify daily and historical commits; the earlier “not enabled” status is superseded. |
| 070 Ember electricity demand and generation | `Ember` | Verified 14 Nov: native raw and nonempty metadata publication; daily/historical routes enabled. No new key needed. |
| 071 WTO Timeseries API; 072 WTO Quantitative Restrictions API; 073 WTO ePing SPS/TBT notifications | `WTO-primary / WTO-secondary` | Verified 14 Nov: all three publish metadata; QR/ePing validators repaired. Provider/network retry findings retained; no new key needed. |
| 075 Copernicus ERA5 / ERA5-Land | `copernicus` | Verified 14 Nov: replacement expired asset downloaded, raw-validated and published. Automatic expiry resubmission installed; structured weather extraction remains pending. No owner action needed. |
| 098 South Korea FSS OpenDART | `dart` | October 26 probe succeeded; October 28 checkup now includes historical request failures. Repair the failing scope and verify daily and historical commits; the earlier “not enabled” status is superseded. |
| 118 US Census International Trade API | `US-census` | October 30: stored key redirects to invalid_key.html. Confirm activation/replace US-census; then engineering retests the exact query. |
| 125 USDA FAS Production, Supply and Distribution | `usda-fas` | Earlier probe returned HTTP 403. Check endpoint/header configuration and the FAS product entitlement; contact FAS only if a correctly authenticated retry is still denied. |
| 074 EPO OPS patent legal events | `EPO-consumer / EPO-consumer-secret` | Verified 14 Nov: original legal XML and metadata publication repaired. Historical m7 capture and daily discovery remain enabled; provider failures retry. No new owner key needed. |

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
| 052 Department of Energy storage program | Earlier public_http_404 retained in old crawl evidence | Reviewed 13 November: corrected storage-only daily/historical frontiers have successful captures without current errors; old off-topic receipts excluded, originals retained. No owner action for the scoped repair. |
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
| 118 | US Census International Trade API (`us_census_international_trade_api`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Access resolved November 4: activated key returned 36 historical rows. Engineering: verify resumed capture and Athena publication. |
| 042 | Tenders Electronic Daily procurement notices (`ted_notices`) | Daily: existing daily schedule; fresh success not audited; historical: 26 succeeded/1 running; structured: 225 complete; 63 partial; 20 failed; 50,399 captured observations | Earlier native audit: 26,907 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 225 complete; 63 partial; 20 failed; 50,399 captured observations. Record-bearing requested task envelope [2017-01-01, 2022-10-01); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q042) | Technical structured-task failures listed above; repair/retry while retaining committed pages. |
| 050 | USGS minerals (`usgs_minerals`) | Raw/SQL rechecked 14 November 2026; current capture/metadata controls and unresolved findings recorded in review evidence | Earlier native audit: 176 committed row occurrences; windows [2021-01-01, 2026-10-23); 2016-era coverage not established Current structured scheduler: 36 complete; 0 partial; 32 failed; 60 captured observations. Record-bearing requested task envelope [2021-01-01, 2026-10-10); not continuous coverage. | REVIEWED — 84 published observations; raw samples passed — [SQL](#q050) | USGS metadata hold and missing-object retry remain open; existing raw/SQL review passed. |
| 017 | FDA openFDA (`fda_openfda`) | Daily: existing daily schedule; fresh success not audited; historical: 116 succeeded/1 pending | Earlier native audit: 9,446 committed row occurrences; windows [2016-01-01, 2026-10-20) | YES — fresh preview returned rows — [SQL](#q017) | October 28: missing-date/duplicate handling deployed; June 2016 replay partial at page limit. Continue and verify publication. |
| 147 | Zenodo research artifacts and usage (`zenodo_research_artifacts_and_usage`) | Daily: structured: 0 complete; 0 partial; 9 failed; 800 captured observations; historical: 42 succeeded/1 pending; structured: 8 complete; 13 partial; 89 failed; 2,650 captured observations | No committed structured-data evidence in earlier native audit. Current structured scheduler: 8 complete; 13 partial; 89 failed; 2,650 captured observations. Record-bearing requested task envelope [2016-01-01, 2016-01-22); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q147) | Technical structured-task failures listed above; repair/retry while retaining committed pages. |
| 143 | DataCite dissertations, datasets, software and usage (`datacite_dissertations_datasets_software_and_usage`) | Daily: structured: 0 complete; 0 partial; 5 failed; 1,300 captured observations; historical: 55 succeeded; structured: 46 complete; 160 partial; 4 failed; 193,140 captured observations | No committed structured-data evidence in earlier native audit. Current structured scheduler: 46 complete; 160 partial; 4 failed; 193,140 captured observations. Record-bearing requested task envelope [2016-01-01, 2021-11-01); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q143) | Technical structured-task failures listed above; repair/retry while retaining committed pages. |
| 145 | bioRxiv / medRxiv preprints (`biorxiv_medrxiv_preprints`) | Daily: structured: 4 complete; 0 partial; 0 failed; 2,109 captured observations; historical: 75 succeeded; structured: 14 complete; 202 partial; 44 failed; 99,185 captured observations | No committed structured-data evidence in earlier native audit. Current structured scheduler: 14 complete; 202 partial; 44 failed; 99,185 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q145) | Pre-June-2019 medRxiv excluded with reviewed evidence; bioRxiv and post-launch failures remain repair work. |
| 075 | Copernicus ERA5 / ERA5-Land (`copernicus_era5_era5_land`) | Reviewed 14 Nov: capture and metadata inspected; exceptions documented | Two complete saved NetCDF artifacts passed checksum/signature checks, including a ZIP with verified NetCDF members; SQL remains nonempty. Found current successful CDS jobs whose download assets had expired. Installed conditional expiry recovery that retains old job receipts and resubmits under the existing two-job limit. A previously failing scope now has a fresh verified NetCDF download and an accepted, published metadata release; exact-job recovery proof is saved separately. Historical and daily lanes remain active. Eight configured reference cells only; structured weather extraction remains pending. | YES — 172 published observations; all declared raw-complete — [SQL](#q075) | Reviewed; see [evidence and open findings](data-collection-processing/repair-notes/2026-11-14-entries-62-75/review-complete.json). |
| 066 | FRED / ALFRED series and vintages (`fred_alfred_series_and_vintages`) | Reviewed 14 Nov: capture and metadata inspected; exceptions documented | Two saved FRED observations matched exact original date/value/realtime intervals. Daily and historical routes are enabled and have successful captures. Open scheduler exceptions include ALFRED vintages the provider says are unavailable, older HTTP 400s and date-scope failures. These remain visible; missing vintages are not synthesized or treated as zeros. Configured series only, not all FRED. | YES — 17,183 published observations; all declared raw-complete — [SQL](#q066) | Reviewed; see [evidence and open findings](data-collection-processing/repair-notes/2026-11-14-entries-62-75/review-complete.json). |
| 125 | USDA FAS Production, Supply and Distribution (`usda_fas_production_supply_and_distribution`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | No structured Athena visibility established; SQL unavailable until publication exists | Existing key/register entry; integration or access validation pending (top). |
| 071 | WTO Timeseries API (`wto_timeseries_api`) | Reviewed 14 Nov: capture and metadata inspected; exceptions documented | Two entire WTO observation rows matched original Dataset responses, including indicator, reporting economy, period, unit and value. Daily/historical routes and metadata are enabled. Saved HTTP/network failures and source-change refreshes remain retryable capture findings; no blanket historical completion claim or all bilateral/product combinations claim. | YES — 22,529 published observations; all declared raw-complete — [SQL](#q071) | Reviewed; see [evidence and open findings](data-collection-processing/repair-notes/2026-11-14-entries-62-75/review-complete.json). |
| 098 | South Korea FSS OpenDART (`south_korea_fss_opendart`) | Daily: not verified active; historical: not verified enabled | No committed structured-data evidence in earlier native audit. | NO rows in fresh preview — [SQL](#q098) | Existing key/register entry; integration or access validation pending (top). |
| 019 | EMA medicines (`ema_medicines`) | Daily: existing daily schedule; fresh success not audited; historical: 1 succeeded; structured: 12 complete; 0 partial; 0 failed; 2,448 captured observations | Earlier native audit: 42,059 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 12 complete; 0 partial; 0 failed; 2,448 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q019) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 026 | Europe PMC publication metadata (`europe_pmc`) | Daily: existing daily schedule; fresh success not audited; historical: 17 succeeded/1 pending; structured: 69 complete; 172 partial; 0 failed; 127,966 captured observations | Earlier native audit: 53,515 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 69 complete; 172 partial; 0 failed; 127,966 captured observations. Record-bearing requested task envelope [2016-01-01, 2023-04-01); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q026) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 027 | Europe PMC full text (`europe_pmc_fulltext`) | Daily: public: 0 files; 10 pages; 32 pending; 1 errors; historical: public: 0 files; 17 pages; 25 pending; 25 errors; 70 succeeded | Earlier native audit: 633 committed row occurrences; windows [2021-01-01, 2026-10-12); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 27 artifact metadata rows visible — [SQL](#q027) | Technical retrieval fixes listed above; no new key established. |
| 041 | USPTO assignment histories (`uspto_assignment_histories`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 116 committed row occurrences; windows [2023-01-01, 2026-10-23); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q041) | Audit/implement historical route and publication; no current enabled historical route established. |
| 024 | NMPA trials (`nmpa_trials`) | Daily: public: 0 files; 1 pages; 2 pending; 2 errors; historical: public: 0 files; 1 pages; 2 pending; 2 errors; 72 succeeded | Earlier native audit: 65,197 committed row occurrences; windows [2021-01-01, 2026-10-16); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 2 artifact metadata rows visible — [SQL](#q024) | October 28: timestamp curation fixed; both failed six-record batches pass locally. Await publisher receipts and Athena queries. |
| 036 | FDA Enforcement Report recalls (`fda_ires_recalls`) | Daily: existing daily schedule; fresh success not audited; historical: 131 succeeded; structured: 100 complete; 1 partial; 30 failed; 135,036 captured observations | Earlier native audit: 31,304 committed row occurrences; windows [2021-01-01, 2026-10-25); 2016-era coverage not established Current structured scheduler: 100 complete; 1 partial; 30 failed; 135,036 captured observations. Record-bearing requested task envelope [2018-03-01, 2026-10-26); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q036) | October 28: empty-response parser deployed; one January 2016 scope complete with zero rows. Reconcile remaining scopes and coverage publication. |
| 057 | BLS wages (`bls_wages`) | Raw/SQL rechecked 14 November 2026; current capture/metadata controls and unresolved findings recorded in review evidence | Earlier native audit: 500 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 6 complete; 0 partial; 6 failed; 69 captured observations. Record-bearing requested task envelope [2021-01-01, 2026-10-10); not continuous coverage. | REVIEWED — 802 published observations; raw samples passed — [SQL](#q057) | Scoped raw/SQL review complete; existing uncommitted inputs and limits remain recorded. |
| 055 | EIA retail prices (`eia_retail_prices`) | Raw/SQL rechecked 14 November 2026; current capture/metadata controls and unresolved findings recorded in review evidence | Earlier native audit: 197 committed row occurrences; windows [2021-01-01, 2026-10-27); 2016-era coverage not established Current structured scheduler: 185 complete; 0 partial; 16 failed; 179 captured observations. Record-bearing requested task envelope [2017-05-01, 2026-09-01); not continuous coverage. | REVIEWED — 322 published observations; raw samples passed — [SQL](#q055) | Scoped raw/SQL review complete; existing uncommitted inputs and limits remain recorded. |
| 056 | California ISO prices (`caiso_prices`) | Raw/SQL rechecked 14 November 2026; current capture/metadata controls and unresolved findings recorded in review evidence | Earlier native audit: 186,766 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 327 complete; 0 partial; 56 failed; 39,240 captured observations. Record-bearing requested task envelope [2023-07-01, 2024-01-07); not continuous coverage. | REVIEWED — 16,256 published observations; raw samples passed — [SQL](#q056) | Scoped raw/SQL review complete; existing uncommitted inputs and limits remain recorded. |
| 070 | Ember electricity demand and generation (`ember_electricity_demand_and_generation`) | Reviewed 14 Nov: capture and metadata inspected; exceptions documented | Corrected validation against the exact archived monthly Ember response, including count, units/aggregation flags and attribution. All 20 formerly failed batches passed original checks, source re-enabled, pending jobs migrated and publication verified. Daily capture is current; historical configured scopes were completed. Missing releases remain missing, not zero. | YES — 2,560 published observations; all declared raw-complete — [SQL](#q070) | Reviewed; see [evidence and open findings](data-collection-processing/repair-notes/2026-11-14-entries-62-75/review-complete.json). |
| 072 | WTO Quantitative Restrictions API (`wto_quantitative_restrictions_api`) | Reviewed 14 Nov: capture and metadata inspected; exceptions documented | Full native restriction/notification JSON is saved under source_documents/wto_quantitative_restrictions_api/, beyond the URL fields visible in normalized rows. Corrected endpoint/identity/date/pagination validation, replayed formerly failed inputs and verified nonempty Athena publication. Daily and configured historical scopes succeeded. Linked documents and current legal effect remain separate. | YES — 1,212 published observations; all declared raw-complete — [SQL](#q072) | Reviewed; see [evidence and open findings](data-collection-processing/repair-notes/2026-11-14-entries-62-75/review-complete.json). |
| 073 | WTO ePing SPS/TBT notifications (`wto_eping_sps_tbt_notifications`) | Reviewed 14 Nov: capture and metadata inspected; exceptions documented | Corrected metadata validation against the exact original ePing notification page and distribution-date query window, including older saved scopes. Replayed and published verified rows. Daily and configured historical captures succeeded. Entire returned English notification metadata is retained; document links are not a claim that attachments were downloaded. | YES — 1,215 published observations; all declared raw-complete — [SQL](#q073) | Reviewed; see [evidence and open findings](data-collection-processing/repair-notes/2026-11-14-entries-62-75/review-complete.json). |
| 051 | UN Comtrade (`un_comtrade`) | Reviewed 13 November 2026; current daily/historical capture and metadata/publication checked | Earlier native audit: 58 committed row occurrences; windows [2021-01-01, 2024-01-01); 2016-era coverage not established Current structured scheduler: 220 complete; 0 partial; 0 failed; 190 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-01-01); not continuous coverage. | REVIEWED — verified metadata-engine observations — [SQL](#q051) | No owner action for the scoped repair; remaining backlog/coverage limits in review evidence |
| 008 | Japan EDINET corporate filings (`edinet_filings`) | Daily: existing daily schedule; fresh success not audited; historical: 34 succeeded; structured: 812 complete; 508 partial; 273 failed; 146,518 captured observations | Earlier native audit: 165,538 committed row occurrences; windows [2021-01-04, 2026-10-26); 2016-era coverage not established Current structured scheduler: 812 complete; 508 partial; 273 failed; 146,518 captured observations. Record-bearing requested task envelope [2021-01-04, 2023-02-07); not continuous coverage. | YES — fresh preview returned rows — [SQL](#q008) | Technical structured-task failures listed above; repair/retry while retaining committed pages. |
| 020 | UK MHRA (`uk_mhra`) | Daily: existing daily schedule; fresh success not audited; historical: 116 succeeded | Earlier native audit: 13,355 committed row occurrences; windows [2021-01-01, 2026-10-16); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q020) | Continue capture/backfill; audit 2016 coverage and publication lag. |
| 021 | Japan PMDA (`japan_pmda`) | Daily: existing daily schedule; fresh success not audited; historical: 15 succeeded | Earlier native audit: 2,950 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established | YES — fresh preview returned rows — [SQL](#q021) | Continue capture/backfill; audit 2016 coverage and publication lag. |
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
| 048 | Federal Register (`federal_register`) | Reviewed 13 November 2026; daily/historical capture and m7 document/metadata schedules checked; both streams enabled | Earlier native audit: 3,513 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 108 complete; 0 partial; 0 failed; 2,027 captured observations. Record-bearing requested task envelope [2016-01-01, 2022-11-01); not continuous coverage. | YES — verified listings and full notices — [SQL](#q048) | Continue existing queues; scoped raw/SQL review complete; current-law/application interpretation remains separate. |
| 049 | Trade screening lists (`trade_screening`) | Daily: public: 3 files; 8 pages; 76 pending; 0 errors; historical: public: 53 files; 87 pages; 1 pending; 1 errors; 71 succeeded | Earlier native audit: 444,362 committed row occurrences; windows [2026-10-09, 2026-10-24); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | REVIEWED 13 Nov — 897 observations / 896 named screening entries; 18 delayed publication batches repaired — [SQL](#q049) | No owner action for this scoped Athena repair; raw backlog and historical coverage remain separate. |
| 052 | Department of Energy storage program (`doe_storage_program`) | Reviewed 13 November 2026; current daily/historical capture and metadata/publication checked | Earlier native audit: 813 committed row occurrences; windows [2026-10-09, 2026-10-24); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | REVIEWED — verified metadata-engine observations — [SQL](#q052) | No owner action for the scoped repair; remaining backlog/coverage limits in review evidence |
| 053 | EIA battery generators (`eia_battery_generators`) | Raw/SQL rechecked 14 November 2026; current capture/metadata controls and unresolved findings recorded in review evidence | Earlier native audit: 76,933 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established Current structured scheduler: 129 complete; 0 partial; 0 failed; 82,938 captured observations. Record-bearing requested task envelope [2016-01-01, 2026-10-01); not continuous coverage. | REVIEWED — 13,085 published observations; raw samples passed — [SQL](#q053) | Scoped raw/SQL review complete; existing uncommitted inputs and limits remain recorded. |
| 054 | EIA generator index (`eia_generator_index`) | Daily: public: 11 files; 1 pages; 39 pending; 0 errors; historical: public: 274 files; 146 pages; 4580 pending; 0 errors; 70 succeeded | Earlier native audit: 2,148 committed row occurrences; windows [2021-01-01, 2026-10-24); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | YES — fresh preview returned rows; 432 artifact metadata rows visible — [SQL](#q054) | Continue crawl; implement dataset extraction/parse and audit dates. |
| 058 | Research Organization Registry institutions (`ror_institutions`) | Raw/SQL rechecked 14 November 2026; current capture/metadata controls and unresolved findings recorded in review evidence | Earlier native audit: 96 committed row occurrences; windows [2026-10-09, 2026-10-10); 2016-era coverage not established; Public route: Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification. No full 2016 coverage verified. | REVIEWED — 141 published observations; raw samples passed — [SQL](#q058) | Scoped raw/SQL review complete; existing uncommitted inputs and limits remain recorded. |
| 060 | DataForSEO search capture (`S65`) | Daily: existing daily schedule; fresh success not audited; historical: not verified enabled | Earlier native audit: 6,464 search/trend/keyword-history sample rows; dated trend/history reaches 2021, search snapshots begin October 2026 | YES — fresh preview returned rows — [SQL](#q060) | Audit/implement historical route and publication; no current enabled historical route established. |
| 062 | SAM.gov opportunities (`sam_gov_opportunities`) | Reviewed 14 Nov: capture and metadata inspected; exceptions documented | Native SAM notice records matched their complete saved search pages. Three older failures (2,009 notices) were generic-validator false negatives; repaired under a notice-metadata contract. Descriptions/attachments are separate linked resources. Daily timer succeeded. The legacy authenticated historical timer remains disabled with migration requirements; no separate SAM historical route was established by this audit. This is an open capture finding, not proof of full history. | YES — 21,790 published observations; all declared raw-complete — [SQL](#q062) | Reviewed; see [evidence and open findings](data-collection-processing/repair-notes/2026-11-14-entries-62-75/review-complete.json). |
| 063 | USPTO Office Actions (`uspto_odp`) | Reviewed 14 Nov: capture and metadata inspected; exceptions documented | Office-action API record and actual USPTO PDF checksum, document/application identity and PDF parse verified. The pasted raw stop was stale: uspto_odp is enabled under contract 2.0.3. Daily and historical prosecution streams share the successful m7 tick. Query now filters patent_office_actions; general patent bibliography cannot satisfy this entry. Ten source-wide inputs remain uncommitted and are withheld until their collection manifests exist. | YES — 95 published observations; all declared raw-complete — [SQL](#q063) | Reviewed; see [evidence and open findings](data-collection-processing/repair-notes/2026-11-14-entries-62-75/review-complete.json). |
| 064 | USPTO final Petition Decisions (`uspto_odp`) | Reviewed 14 Nov: capture and metadata inspected; exceptions documented | Petition-decision API record and actual USPTO PDF checksum, application identity and PDF parse verified. Daily and historical prosecution streams share the successful m7 tick. Query now filters patent_petition_decisions. Ten source-wide uncommitted inputs remain withheld; no claim of exhaustive prosecution history. | YES — 95 published observations; all declared raw-complete — [SQL](#q064) | Reviewed; see [evidence and open findings](data-collection-processing/repair-notes/2026-11-14-entries-62-75/review-complete.json). |
| 065 | BIS SDMX API (`bis_sdmx_api`) | Reviewed 14 Nov: capture and metadata inspected; exceptions documented | The missing folder was an incorrect locator. Native policy-rate CSVs are under constellation-backfill/public-capture/objects/bis_sdmx_api/. Two complete files (about 59 MB each) passed SHA-256/size and CSV-header checks on m7. Daily frontier succeeded today, historical file route is drained. SQL counts archived-file metadata, not individual policy-rate measurements; selected BIS dataflow only. | YES — 8 published file-metadata rows; all declared raw-complete — [SQL](#q065) | Reviewed; see [evidence and open findings](data-collection-processing/repair-notes/2026-11-14-entries-62-75/review-complete.json). |
| 067 | UNIDO IIP and INDSTAT (`unido_iip_and_indstat`) | Reviewed 14 Nov: capture and metadata inspected; exceptions documented | Old SQL rows described catalogues, not industrial measurements. Added native UNIDO getData capture with dynamic dataset IDs and country/variable/activity/period provenance, plus m7 historical dispatch and daily rotation. Historical and daily proof captures passed for both IIP and INDSTAT/4. Suppressed/aggregation footnote cells are retained without inventing zeros. SQL below excludes legacy public_documents catalogues. Backfill remains in progress. | YES — 1,056 published observations; all declared raw-complete — [SQL](#q067) | Reviewed; see [evidence and open findings](data-collection-processing/repair-notes/2026-11-14-entries-62-75/review-complete.json). |
| 068 | ILOSTAT labor statistics (`ilostat_labor_statistics`) | Reviewed 14 Nov: capture and metadata inspected; exceptions documented | The missing folder was an incorrect locator. Original gzip-compressed RDS files are under constellation-backfill/public-capture/objects/ilostat_labor_statistics/. Two files passed SHA-256/size, full gzip integrity and R serialization framing checks. Daily frontier succeeded today; historical snapshot route is drained. SQL rows describe archived files, not extracted labor observations. Forecast/observation and vintage extraction remain unimplemented. | YES — 8 published file-metadata rows; all declared raw-complete — [SQL](#q068) | Reviewed; see [evidence and open findings](data-collection-processing/repair-notes/2026-11-14-entries-62-75/review-complete.json). |
| 069 | IMF PortWatch shipping activity (`imf_portwatch_shipping_activity`) | Reviewed 14 Nov: capture and metadata inspected; exceptions documented | Replaced website-discovery-only input with the IMF native ArcGIS port/day table. m7 captured and validated all 2,065 port rows for 2019-01-01 and for 2026-11-06, then published metadata. Recurring historical dispatcher and m7 daily rotation are active; obsolete discovery inputs were superseded with evidence retained. Provider availability starts 2019-01-01, not 2016; daily uses a seven-day lag. Estimates are not customs shipments; backfill is ongoing. | YES — 993 published observations; all declared raw-complete — [SQL](#q069) | Reviewed; see [evidence and open findings](data-collection-processing/repair-notes/2026-11-14-entries-62-75/review-complete.json). |
| 074 | EPO OPS patent legal events (`epo_ops_patent_legal_events`) | Reviewed 14 Nov: capture and metadata inspected; exceptions documented | Corrected validation of original EPO legal-event XML, event/family identity and distinct gazette/effective/created/exchanged dates; replayed and published verified rows. Daily/historical capture remains enabled, with older provider HTTP 500s and quota deferrals recorded. Candidate applicant matches and current legal title are unverified. | YES — 227 published observations; all declared raw-complete — [SQL](#q074) | Reviewed; see [evidence and open findings](data-collection-processing/repair-notes/2026-11-14-entries-62-75/review-complete.json). |
| 076 | NASA POWER weather and solar resource (`nasa_power_weather_and_solar_resource`) | Daily and historical enabled; metadata queue enabled | Native NASA measurements were checked against the saved complete provider response, including parameter values and units. Daily capture and the configured historical scopes are healthy; the eight reference locations are a bounded geographic scope. | YES — 135 complete rows in bounded published sample — [SQL](#q076) | Reviewed 16 Nov 2026; [evidence](data-collection-processing/repair-notes/2026-11-16-entries-76-90/review-report.md). |
| 077 | USGS Earthquake Catalog API (`usgs_earthquakes`) | Daily and historical enabled; metadata queue enabled | The missing folder was a locator error. Daily GeoJSON originals live under public-capture/objects/usgs_earthquakes; historical originals are linked from native job manifests. All 3,951 registered historical query partitions succeeded and the seven current daily windows completed; this does not certify every possible earthquake query or original vintage. | YES — 128 complete rows in bounded published sample — [SQL](#q077) | Reviewed 16 Nov 2026; [evidence](data-collection-processing/repair-notes/2026-11-16-entries-76-90/review-report.md). |
| 078 | UCDP organized violence (`ucdp_organized_violence`) | Daily and historical enabled; metadata queue enabled | Added official UCDP GED ZIP and candidate CSV acquisition, checksums, whole-archive CRC/structure checks, metadata validation and publication. Daily and historical public-file routes completed their present frontiers. Public downloads work without the separately authenticated UCDP API. | YES — 2 complete rows in bounded published sample — [SQL](#q078) | Reviewed 16 Nov 2026; [evidence](data-collection-processing/repair-notes/2026-11-16-entries-76-90/review-report.md). |
| 079 | arXiv early technical disclosures (`arxiv`) | Daily and historical enabled; metadata queue enabled | Citation and abstract processing is repaired and published under contract 2.0.3; all 400 records from the four former failed batches matched saved Atom originals. These are metadata/abstracts, not full papers. Full-text acquisition remains outstanding, so this entry is not fully reviewed. An older daily snapshot stopped on duplicate provider IDs; its replacement query completed with 1,647 records, all were validated against native Atom originals, and only the exact incomplete metadata input was superseded. Original bytes remain retained; replacement metadata processing is queued. | YES — 104 complete rows in bounded published sample — [SQL](#q079) | Partial; full text outstanding; [evidence](data-collection-processing/repair-notes/2026-11-16-entries-76-90/review-report.md). |
| 080 | England NHSBSA prescribing data (`england_nhsbsa_prescribing_data`) | Daily and historical enabled; metadata queue enabled | Replaced catalogue-only input with native, full-field prescribing rows. Daily collection prefers the current SNOMED catalogue, whose latest probed release is August 2026; the retired catalogue remains available for older months. Verified 1,000 January-2016 rows and 1,000 August-2026 rows. Pagination continues; neither month nor the full history is claimed complete. | YES — 160 complete rows in bounded published sample — [SQL](#q080) | Reviewed 16 Nov 2026; [evidence](data-collection-processing/repair-notes/2026-11-16-entries-76-90/review-report.md). |
| 081 | Decodo shared web retrieval (access layer) (`decodo_shared_web_retrieval_access_layer`) | Reviewed access layer; used by dependent daily/historical capture | Reviewed as an access layer: successful CDA-AMC retrieval and strict base64-PDF recovery verified the gateway. Standalone raw folders and source_observations rows are not applicable; dependent sources own their original artifacts and observations. | N/A — access layer; no standalone dataset — [SQL](#q081) | Reviewed 16 Nov 2026; [evidence](data-collection-processing/repair-notes/2026-11-16-entries-76-90/review-report.md). |
| 082 | SIA / WSTS public semiconductor sales (`sia_wsts_public_semiconductor_sales`) | Daily and historical enabled; metadata queue enabled | Located and verified the complete saved WSTS billings PDF and restored scoped native-file publication. The old August URL now returns 404, while its archived original remains intact; current daily and historical index discovery completed without download failures. | YES — 1 complete rows in bounded published sample — [SQL](#q082) | Reviewed 16 Nov 2026; [evidence](data-collection-processing/repair-notes/2026-11-16-entries-76-90/review-report.md). |
| 083 | SEMI worldwide equipment billings (`semi_worldwide_equipment_billings`) | Daily and historical enabled; metadata queue enabled | Moved discovery to the working official SEAJ index and followed only its worldwide SEMS rows, excluding Japan-only and FPD rows. The joint SEMI/SEAJ worldwide PDFs and back-number PDF are captured; daily and historical crawls are healthy. Paid detailed WWSEMS products are excluded. | YES — 1 complete rows in bounded published sample — [SQL](#q083) | Reviewed 16 Nov 2026; [evidence](data-collection-processing/repair-notes/2026-11-16-entries-76-90/review-report.md). |
| 084 | International Federation of Robotics World Robotics (`international_federation_of_robotics_world_robotics`) | Daily and historical enabled; metadata queue enabled | Rejected images and discovery pages as reports; verified the complete public 2025 World Robotics executive-summary PDF and published its native-file metadata. Daily and historical discovery continue. This does not assert a paid full database or that the 2025 summary is a 2026 release. | YES — 1 complete rows in bounded published sample — [SQL](#q084) | Reviewed 16 Nov 2026; [evidence](data-collection-processing/repair-notes/2026-11-16-entries-76-90/review-report.md). |
| 085 | IEA-PVPS solar deployment reports (`iea_pvps_solar_deployment_reports`) | Daily and historical enabled; metadata queue enabled | Verified the actual Snapshot of Global PV Markets 2026 PDF, excluded unrelated technical files, and replaced the broken trends index with the working publications index. Daily and historical capture are healthy; additional public reports continue through the queue. | YES — 1 complete rows in bounded published sample — [SQL](#q085) | Reviewed 16 Nov 2026; [evidence](data-collection-processing/repair-notes/2026-11-16-entries-76-90/review-report.md). |
| 086 | Germany G-BA drug benefit assessments (`germany_g_ba_drug_benefit_assessments`) | Daily and historical enabled; metadata queue enabled | Restricted discovery to benefit-assessment cases and original dossier/assessment PDFs. Verified an original IQWiG/G-BA benefit-assessment PDF and its published metadata. Daily and historical discovery continue; no clinical or reimbursement interpretation is inferred. | YES — 1 complete rows in bounded published sample — [SQL](#q086) | Reviewed 16 Nov 2026; [evidence](data-collection-processing/repair-notes/2026-11-16-entries-76-90/review-report.md). |
| 087 | France HAS medicine assessment opinions (`france_has_medicine_assessment_opinions`) | Daily and historical enabled; metadata queue enabled | Fixed HAS relative links, native CP1252/dollar-quoted CSV validation, and its headerless CT-to-opinion URL export. SMR/ASMR originals and a final committee-opinion PDF are verified and published. All daily download errors recovered. Discovered 10,490 opinion links and restored about 5,000 within the existing frontier cap; historical processing is active and full coverage remains open. | YES — 5 complete rows in bounded published sample — [SQL](#q087) | Reviewed 16 Nov 2026; [evidence](data-collection-processing/repair-notes/2026-11-16-entries-76-90/review-report.md). |
| 089 | Canada CDA-AMC / CADTH reimbursement reviews (`canada_cda_amc_cadth_reimbursement_reviews`) | Daily and historical enabled; metadata queue enabled | Fixed gateway base64 PDFs that had been mislabelled HTML, preserving the original gateway wrapper separately. Verified and published a final CDA-AMC reimbursement recommendation PDF as well as the separately labelled patient/clinician input. Daily and historical public-file crawls completed their current frontiers; exhaustive review history and clinical interpretation are not asserted. | YES — 2 complete rows in bounded published sample — [SQL](#q089) | Reviewed 16 Nov 2026; [evidence](data-collection-processing/repair-notes/2026-11-16-entries-76-90/review-report.md). |
| 090 | France Assurance Maladie Open Medic (`france_assurance_maladie_open_medic`) | Daily and historical enabled; metadata queue enabled | Corrected the provider download host, catalogue/document classification and fresh public download-link resolution. Verified the complete 2025 Open Medic ZIP, checksum and every member CRC. Daily and historical capture are active. SQL rows represent validated original annual dataset files; individual medicine/cost-row extraction is a separate downstream step. | YES — 1 complete rows in bounded published sample — [SQL](#q090) | Reviewed 16 Nov 2026; [evidence](data-collection-processing/repair-notes/2026-11-16-entries-76-90/review-report.md). |
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
| 088 | NICE technology appraisals (`nice_technology_appraisals`) | PAUSED — owner licensing/security hold preserved | Deliberate owner pause preserved. NICE capture and AI processing were not resumed and no fresh provider request was made. The existing licensed API, cybersecurity review and owner authorization requirements remain; no completed review is claimed. | Not queried during the pause — [SQL](#q088) | Owner pause; not reviewed; [evidence](data-collection-processing/repair-notes/2026-11-16-entries-76-90/review-report.md). |

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

**046. MLPerf benchmark results — reviewed 13 November 2026**

Published benchmark results; file inventories and supporting logs are separate kinds. Workgroup: `optima-collected-data`, us-east-1, AwsDataCatalog, result reuse off.

```sql
SELECT source_key, record_kind, source_record_id, ingested_at,
       raw_completeness_status,
       json_extract(labelled_json, '$.payload.data') AS provider_data,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key = 'mlperf_results'
  AND record_kind = 'benchmark_result'
LIMIT 25;
```

### q047

**047. CPSC recalls — reviewed 13 November 2026**

Full original recall fields and evidence; image URLs do not imply downloaded images. Workgroup: `optima-collected-data`, us-east-1, AwsDataCatalog, result reuse off.

```sql
SELECT source_key, record_kind, source_record_id, ingested_at,
       raw_completeness_status,
       json_extract(labelled_json, '$.payload.data') AS provider_data,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key = 'cpsc_recalls'
LIMIT 25;
```

### q048

**048. Federal Register — reviewed 13 November 2026**

Workgroup: `optima-collected-data`, us-east-1, AwsDataCatalog, result reuse off. Listings and full notices have separate source keys and record kinds. Full notice text/provisions are in `payload.data.enrichment`; oversized complete extractions are linked through `full_extraction_source`.

```sql
SELECT source_key, record_kind, source_record_id, ingested_at,
       raw_completeness_status,
       json_extract(labelled_json, '$.payload.data') AS provider_data,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key IN ('federal_register','federal_register_documents')
LIMIT 25;
```

### q049

**049. Trade screening lists — reviewed 13 November 2026**

Workgroup: `optima-collected-data`, us-east-1, AwsDataCatalog, result reuse off. The old preview used `LIMIT 1`; summary/count queries return one aggregate row. This query returns individual named provider entries, excluding the older archive-only receipt. Retired tracking enrichment is not part of the active pipeline.

```sql
SELECT source_key, source_record_id, record_kind, ingested_at,
       raw_completeness_status,
       json_extract_scalar(labelled_json, '$.payload.data.id') AS provider_id,
       json_extract_scalar(labelled_json, '$.payload.data.name') AS name,
       json_extract_scalar(labelled_json, '$.payload.data.source') AS provider_list,
       json_extract(labelled_json, '$.payload.data') AS provider_data,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key = 'trade_screening'
  AND json_extract_scalar(labelled_json, '$.payload.data.name') IS NOT NULL
LIMIT 25;
```

Verified snapshot: **897 observations / 896 named entries**, including **576 observations in 18 repaired publication batches**. Counts are occurrences, not unique screened entities. [Summary and detail queries](data-collection-processing/repair-notes/2026-11-13-trade-screening/review-queries.sql).

### q050

**050. USGS minerals — reviewed 14 November 2026 (existing raw/SQL scope)**

Workgroup: `optima-collected-data`, us-east-1, AwsDataCatalog, result reuse off. Two 2026 lithium/cobalt PDFs matched their originals, reparsed text, statistics, footnotes and sections. The background metadata queue remains **raw_stopped** after four older validation failures, plus one missing-object retry; this finding is open. Published rows remain queryable. This checkbox covers existing raw material/SQL, not recovery of that queue or full history.

```sql
SELECT source_key, dataset, source_record_id, ingested_at,
       raw_completeness_status,
       json_extract(labelled_json, '$.payload.data') AS provider_data,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key = 'usgs_minerals'
  AND dataset = 'specialist_inputs'
  AND json_extract(labelled_json, '$.payload.data') IS NOT NULL
LIMIT 25;
```

Verified snapshot: **84 published observation occurrences**. [Queries with bounded published-partition examples](data-collection-processing/repair-notes/2026-11-14-six-source-review/review-queries.sql).

### q051

**051. UN Comtrade — reviewed 13 November 2026**

Workgroup: `optima-collected-data`, us-east-1, AwsDataCatalog, result reuse off. Entire provider rows retain original units, nulls and estimation flags; the configured annual trade scope is not all trade.

```sql
SELECT source_key, record_kind, source_record_id, ingested_at,
       raw_completeness_status,
       json_extract(labelled_json, '$.payload.data') AS provider_data,
       json_extract(labelled_json, '$.payload.extraction_reference') AS saved_extraction,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key = 'un_comtrade'
LIMIT 25;
```

[Verified summary and detail queries](data-collection-processing/repair-notes/2026-11-13-comtrade-doe/review-queries.sql).

### q052

**052. Department of Energy storage program — reviewed 13 November 2026**

Workgroup: `optima-collected-data`, us-east-1, AwsDataCatalog, result reuse off. Program pages, originals, technical statements and funding statements have separate record kinds. Full saved extractions are linked; statements are not certified measurements or payments.

```sql
SELECT source_key, record_kind, source_record_id, ingested_at,
       raw_completeness_status,
       json_extract(labelled_json, '$.payload.data') AS provider_data,
       json_extract(labelled_json, '$.payload.extraction_reference') AS saved_extraction,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key IN ('doe_storage_program','doe_storage_documents','doe_storage_benchmarks','doe_storage_funding')
LIMIT 25;
```

[Verified summary and detail queries](data-collection-processing/repair-notes/2026-11-13-comtrade-doe/review-queries.sql).

### q053

**053. EIA battery generators — reviewed 14 November 2026 (existing raw/SQL scope)**

Workgroup: `optima-collected-data`, us-east-1, AwsDataCatalog, result reuse off. Two September 2026 Planned/Operating generator rows matched the official workbook, sheet, Plant ID, Generator ID and all retained columns. Inventory statuses/units remain explicit; dispatch, firm capacity and supplier/entity matching are outside scope. The source is enabled; two older inputs lacking checkpoint evidence remain excluded.

```sql
SELECT source_key, dataset, source_record_id, ingested_at,
       raw_completeness_status,
       json_extract(labelled_json, '$.payload.data') AS provider_data,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key = 'eia_battery_generators'
  AND dataset = 'specialist_inputs'
  AND json_extract(labelled_json, '$.payload.data') IS NOT NULL
LIMIT 25;
```

Verified snapshot: **13,085 published observation occurrences**. [Queries with bounded published-partition examples](data-collection-processing/repair-notes/2026-11-14-six-source-review/review-queries.sql).

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

**055. EIA retail prices — reviewed 14 November 2026 (existing raw/SQL scope)**

Workgroup: `optima-collected-data`, us-east-1, AwsDataCatalog, result reuse off. Two saved US/all-sector monthly rows matched original API responses, identities and price/sales/revenue/customer units. These are average retail statistics, not wholesale prices or site tariffs. Source enabled; no failed/retry/uncommitted metadata jobs in the scoped control check.

```sql
SELECT source_key, dataset, source_record_id, ingested_at,
       raw_completeness_status,
       json_extract(labelled_json, '$.payload.data') AS provider_data,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key = 'eia_retail_prices'
  AND dataset = 'specialist_inputs'
  AND json_extract(labelled_json, '$.payload.data') IS NOT NULL
LIMIT 25;
```

Verified snapshot: **322 published observation occurrences**. [Queries with bounded published-partition examples](data-collection-processing/repair-notes/2026-11-14-six-source-review/review-queries.sql).

### q056

**056. California ISO prices — reviewed 14 November 2026 (existing raw/SQL scope)**

Workgroup: `optima-collected-data`, us-east-1, AwsDataCatalog, result reuse off. Two DAM price components matched official ZIP/member provenance, exact native rows, prices and interval timing. Negative values are retained. This covers caiso_prices only, not all nodes, ancillary datasets, storage indicators or profitability. Source enabled; one older input lacking checkpoint evidence remains excluded.

```sql
SELECT source_key, dataset, source_record_id, ingested_at,
       raw_completeness_status,
       json_extract(labelled_json, '$.payload.data') AS provider_data,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key = 'caiso_prices'
  AND dataset = 'specialist_inputs'
  AND json_extract(labelled_json, '$.payload.data') IS NOT NULL
LIMIT 25;
```

Verified snapshot: **16,256 published observation occurrences**. [Queries with bounded published-partition examples](data-collection-processing/repair-notes/2026-11-14-six-source-review/review-queries.sql).

### q057

**057. BLS wages — reviewed 14 November 2026 (existing raw/SQL scope)**

Workgroup: `optima-collected-data`, us-east-1, AwsDataCatalog, result reuse off. Two CES3000000003 observations matched original BLS series rows, periods, values and footnotes. Units are seasonally adjusted manufacturing average hourly earnings in USD/hour, not fully loaded customer labor costs. Source enabled; two older inputs lacking checkpoint evidence remain excluded.

```sql
SELECT source_key, dataset, source_record_id, ingested_at,
       raw_completeness_status,
       json_extract(labelled_json, '$.payload.data') AS provider_data,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key = 'bls_wages'
  AND dataset = 'specialist_inputs'
  AND json_extract(labelled_json, '$.payload.data') IS NOT NULL
LIMIT 25;
```

Verified snapshot: **802 published observation occurrences**. [Queries with bounded published-partition examples](data-collection-processing/repair-notes/2026-11-14-six-source-review/review-queries.sql).

### q058

**058. Research Organization Registry institutions — reviewed 14 November 2026 (existing raw/SQL scope)**

Workgroup: `optima-collected-data`, us-east-1, AwsDataCatalog, result reuse off. Two entire institution records matched original ROR v2 responses, IDs, names, relationships and status. These are current identity candidates, not verified grant affiliations or historical vintages. Source enabled; one older public-receipt validation failure and two uncommitted inputs remain recorded.

```sql
SELECT source_key, dataset, source_record_id, ingested_at,
       raw_completeness_status,
       json_extract(labelled_json, '$.payload.data') AS provider_data,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key = 'ror_institutions'
  AND dataset = 'specialist_inputs'
  AND json_extract(labelled_json, '$.payload.data') IS NOT NULL
LIMIT 25;
```

Verified snapshot: **141 published observation occurrences**. [Queries with bounded published-partition examples](data-collection-processing/repair-notes/2026-11-14-six-source-review/review-queries.sql).

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

Verified metadata readback (14 Nov 2026); declared raw/file scope and remaining capture findings are in the review evidence. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'sam_gov_opportunities' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;
```

### q063

**063. USPTO Office Actions**

Verified metadata readback (14 Nov 2026); declared raw/file scope and remaining capture findings are in the review evidence. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'uspto_odp' AND dataset = 'patent_office_actions' GROUP BY source_key, dataset;
```

### q064

**064. USPTO final Petition Decisions**

Verified metadata readback (14 Nov 2026); declared raw/file scope and remaining capture findings are in the review evidence. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'uspto_odp' AND dataset = 'patent_petition_decisions' GROUP BY source_key, dataset;
```

### q065

**065. BIS SDMX API**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'bis_sdmx_api' AND dataset = 'public_documents' GROUP BY source_key, dataset;
```

### q066

**066. FRED / ALFRED series and vintages**

Verified metadata readback (14 Nov 2026); declared raw/file scope and remaining capture findings are in the review evidence. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'fred_alfred_series_and_vintages' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;
```

### q067

**067. UNIDO IIP and INDSTAT**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'unido_iip_and_indstat' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;
```

### q068

**068. ILOSTAT labor statistics**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'ilostat_labor_statistics' AND dataset = 'public_documents' GROUP BY source_key, dataset;
```

### q069

**069. IMF PortWatch shipping activity**

Artifact metadata only. Workgroup: `optima-regulatory-pilot`.

```sql
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'imf_portwatch_shipping_activity' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;
```

### q070

**070. ember_electricity_demand_and_generation**

Verified metadata readback. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'ember_electricity_demand_and_generation' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;
```

### q071

**071. wto_timeseries_api**

Verified metadata readback. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'wto_timeseries_api' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;
```

### q072

**072. wto_quantitative_restrictions_api**

Verified metadata readback. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'wto_quantitative_restrictions_api' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;
```

### q073

**073. wto_eping_sps_tbt_notifications**

Verified metadata readback. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'wto_eping_sps_tbt_notifications' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;
```

### q074

**074. EPO OPS patent legal events**

Verified metadata readback (14 Nov 2026); declared raw/file scope and remaining capture findings are in the review evidence. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'epo_ops_patent_legal_events' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;
```

### q075

**075. copernicus_era5_era5_land**

Verified metadata readback. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_batches, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = 'copernicus_era5_era5_land' AND dataset = 'specialist_inputs' GROUP BY source_key, dataset;
```

### q076

**076. NASA POWER weather and solar resource**

Verified published sample, up to five jobs; these counts are not the full source inventory. Workgroup: `optima-collected-data`. Public-file sources count validated original files, while NASA/USGS/NHSBSA/arXiv count source rows. Native originals are linked separately from collected envelopes.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'nasa_power_weather_and_solar_resource' AND contract_version = '2.0.2' AND job_id IN ('002565768e416cb6727c726186823352ea2537160b7ed5d090120cd8cbd2a4e6', '00eed946e9b41bf6153e1442692e8d2e79a9a540e68b377d83175bf468fc4f4c', '01507966c490f7590ae0a7954df1e143d6d7693f21b5634673052fbe8612b0f3', '017eec1ee3c217e279a30eddcbfd6ac89d98cfa9e899b80430221a8bd8e43205', '018a01f18a5ce8a19e1c7e684b2938330adb8f2ace1193ddcbde1cf01008e00c') GROUP BY source_key, dataset;
```

### q077

**077. USGS Earthquake Catalog API**

Verified published sample, up to five jobs; these counts are not the full source inventory. Workgroup: `optima-collected-data`. Public-file sources count validated original files, while NASA/USGS/NHSBSA/arXiv count source rows. Native originals are linked separately from collected envelopes.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'usgs_earthquakes' AND contract_version = '2.0.2' AND job_id IN ('00ba868baf2b73d76073980ee5514974f97bd2d76f9237d78ed9c5f3f73c9b31', '012e78fe7260b3629dcd9f24a566b98aafecf60c212202eb1daf40ceffe1a94a', '01b84b0dfab55ed568e76267b227fab2961a9a3ed8bb27d44a700ff40181a681', '01bbde93ee3a577de5f94fe26998d796167aae269cb8a457c3eac004939ffee9') GROUP BY source_key, dataset;
```

### q078

**078. UCDP organized violence**

Verified published sample, up to five jobs; these counts are not the full source inventory. Workgroup: `optima-collected-data`. Public-file sources count validated original files, while NASA/USGS/NHSBSA/arXiv count source rows. Native originals are linked separately from collected envelopes.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'ucdp_organized_violence' AND contract_version = '2.0.3' AND job_id IN ('43ebe1db1e0a565738657a3e79166136fc272276db63809ce8ae0938495805d0', '9abe4a47193d54e81ee70157858b0cad93c6aa22a94b7cadf74561415e371878') GROUP BY source_key, dataset;
```

### q079

**079. arXiv early technical disclosures**

Verified published sample, up to five jobs; these counts are not the full source inventory. Workgroup: `optima-collected-data`. Public-file sources count validated original files, while NASA/USGS/NHSBSA/arXiv count source rows. Native originals are linked separately from collected envelopes.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'arxiv' AND contract_version = '2.0.3' AND job_id IN ('0eda391b934be0f3bd7b88a36ee572a652f3309fd46e1d031d32188773ddcc1b', '1d22ad5a415479481a7fff7d3faf0a1d63f2ef479bf387cccdaca8206aa546e9', '30587ca1f2be9650772f684032adf2a9aa96ee1341378e151930a092868d86b6', '36b2d8c47ae1f352f9cacda68af1f99ed32e269f08cdfb176e63859cd04697d1', '370d35cf12eceee55049b7e0ed8f26853e0a55ce7c125247c4dcb6ece3bbdae7') GROUP BY source_key, dataset;
```

### q080

**080. England NHSBSA prescribing data**

Verified published sample, up to five jobs; these counts are not the full source inventory. Workgroup: `optima-collected-data`. Public-file sources count validated original files, while NASA/USGS/NHSBSA/arXiv count source rows. Native originals are linked separately from collected envelopes.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'england_nhsbsa_prescribing_data' AND contract_version = '2.0.3' AND job_id IN ('01e15bfae93a53f2eaf2edaad8dba27d1d9fc9edef8d948c56981969fb7a05bf', '0284438d4829006f6ec019be12bdd7317d172cd0e20351d9f3eba4cfc34964b5', '038303d3f9d1403ddd244ad8a490b98519f6f85bf7b3d244ff5576ba15f244b8', '05c01b2c9f684c9b24c136aa9761cbfe2a1a5aae3b8311cacef739cf3487e0a3', '0da7408f9c038518577228312c0a5cd89dbb72497f0bc02ee252fdc975c3f08c') GROUP BY source_key, dataset;
```

### q081

**081. Decodo shared web retrieval (access layer)**

Access-layer verification; no standalone query.

```sql
-- Decodo is a retrieval access layer; standalone source rows are not applicable.
```

### q082

**082. SIA / WSTS public semiconductor sales**

Verified published sample, up to five jobs; these counts are not the full source inventory. Workgroup: `optima-collected-data`. Public-file sources count validated original files, while NASA/USGS/NHSBSA/arXiv count source rows. Native originals are linked separately from collected envelopes.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'sia_wsts_public_semiconductor_sales' AND contract_version = '2.0.3' AND job_id IN ('eb06a5d04d093727576a87a96813262a26d2968aefdd4acab1b9c62e1c26b614') GROUP BY source_key, dataset;
```

### q083

**083. SEMI worldwide equipment billings**

Verified published sample, up to five jobs; these counts are not the full source inventory. Workgroup: `optima-collected-data`. Public-file sources count validated original files, while NASA/USGS/NHSBSA/arXiv count source rows. Native originals are linked separately from collected envelopes.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'semi_worldwide_equipment_billings' AND contract_version = '2.0.3' AND job_id IN ('493af9a0638ac3d7a5ef1148d0d602944c305bdb063c45d5183468f0070906d4') GROUP BY source_key, dataset;
```

### q084

**084. International Federation of Robotics World Robotics**

Verified published sample, up to five jobs; these counts are not the full source inventory. Workgroup: `optima-collected-data`. Public-file sources count validated original files, while NASA/USGS/NHSBSA/arXiv count source rows. Native originals are linked separately from collected envelopes.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'international_federation_of_robotics_world_robotics' AND contract_version = '2.0.3' AND job_id IN ('b956eb4b673a4546ebd03266e4cf32bc5697a85343379433826835297d7e384a') GROUP BY source_key, dataset;
```

### q085

**085. IEA-PVPS solar deployment reports**

Verified published sample, up to five jobs; these counts are not the full source inventory. Workgroup: `optima-collected-data`. Public-file sources count validated original files, while NASA/USGS/NHSBSA/arXiv count source rows. Native originals are linked separately from collected envelopes.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'iea_pvps_solar_deployment_reports' AND contract_version = '2.0.3' AND job_id IN ('97fb4e95091dde3f22dba4e0a8358fa9780738d1a31bda54e4374cf51ed2b06b') GROUP BY source_key, dataset;
```

### q086

**086. Germany G-BA drug benefit assessments**

Verified published sample, up to five jobs; these counts are not the full source inventory. Workgroup: `optima-collected-data`. Public-file sources count validated original files, while NASA/USGS/NHSBSA/arXiv count source rows. Native originals are linked separately from collected envelopes.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'germany_g_ba_drug_benefit_assessments' AND contract_version = '2.0.3' AND job_id IN ('b0c60b7e25484fc3bea15927f58fe66d94210f673af49293e37af116484f4b40') GROUP BY source_key, dataset;
```

### q087

**087. France HAS medicine assessment opinions**

Verified published sample, up to five jobs; these counts are not the full source inventory. Workgroup: `optima-collected-data`. Public-file sources count validated original files, while NASA/USGS/NHSBSA/arXiv count source rows. Native originals are linked separately from collected envelopes.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'france_has_medicine_assessment_opinions' AND contract_version = '2.0.3' AND job_id IN ('451cbaabfed1ccc9296116b5b9d0648060021271e1d891adcb1d2d19c3a29ae9', '6bad4a342934cb2ae660edf143542bec0d92d88619aee3f2871676debf5017d3', 'dc312d7a3bfd9e272c25fbde42c02148820a478ca6186ae0ce0607d7ae3644c6', 'de55a7825bfec23ad5d44a27d9da52c2bc7261aad15e8d7615d5490d27efd797', 'e8115c9f77af2b551a5d76b239017a447d8d8f00352daa3049df0879cfeb9078') GROUP BY source_key, dataset;
```

### q088

**088. NICE technology appraisals**

Intentionally paused. Retained-data query shown only; no query was run during this review.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'nice_technology_appraisals' GROUP BY source_key, dataset;
```

### q089

**089. Canada CDA-AMC / CADTH reimbursement reviews**

Verified published sample, up to five jobs; these counts are not the full source inventory. Workgroup: `optima-collected-data`. Public-file sources count validated original files, while NASA/USGS/NHSBSA/arXiv count source rows. Native originals are linked separately from collected envelopes.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'canada_cda_amc_cadth_reimbursement_reviews' AND contract_version = '2.0.3' AND job_id IN ('2e31bf1b92a6f506cc9ac059c6dd7bbe3f9ecbead040324ac9e6f645aac9542c', '7cffc150b76ee4c1805246957e707049b0068ae3c4c67d1861d9b2e92bd1577d') GROUP BY source_key, dataset;
```

### q090

**090. France Assurance Maladie Open Medic**

Verified published sample, up to five jobs; these counts are not the full source inventory. Workgroup: `optima-collected-data`. Public-file sources count validated original files, while NASA/USGS/NHSBSA/arXiv count source rows. Native originals are linked separately from collected envelopes.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'france_assurance_maladie_open_medic' AND contract_version = '2.0.3' AND job_id IN ('d19394d3b1f339cff55f60225b27ab76f369093a835d297d4eb043ec8ba642c9') GROUP BY source_key, dataset;
```

### q091

**091. Japan MHLW NDB Open Data**

Review (18 November 2026): **reviewed**. SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Exact verified published jobs are selected below; this is a bounded verification sample, not the full inventory. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'japan_mhlw_ndb_open_data' AND contract_version = '2.0.3' AND job_id IN ('7c34c24f400ccf32f7ce9dfeceba40fd63fd4695f8f9b99a047fb2e99e69f2d0') GROUP BY source_key, dataset;
```

[Repair evidence and remaining gaps](/home/ec2-user/data-collection-processing/repair-notes/2026-11-18-entries-91-105/review-status.json).

### q092

**092. CNINFO mainland-China company disclosures**

Review (18 November 2026): **reviewed**. Complete native filing-index row paired with its original PDF/XML document; no XBRL fact extraction or historical-vintage inference. Exact verified published jobs are selected below; this is a bounded verification sample, not the full inventory. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[2].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'cninfo_mainland_china_company_disclosures' AND contract_version = '2.0.3' AND job_id IN ('a45a0e1352b43705a8e9d1ce84d32bafacd533f8b7b17cd4230fefaddce7129b','7d181e0aee47b53e0446336368bf44212d5c43cb01e02a9cbbc4a35dec0f8899','42a0e57e271a43ea915dd17e9ed83903ca1cc47f5409d6ed1192c60e7cc7e33c','dcbf4e73206b780092970a5055bdbd4603cacc02241b8a946fce4726b626da43','a6394933a32c50c141df931d5ea350d92b4684749617ece46864701e8039d92b','5e0cf8b71ded7c8c60ca3e9ba0b2733d00a1ce419f70ad950af8b207c50beffc','8eada9c24d52409b84150eb84e9e98a0b2fd8ee64a4b0a7684f7ab6a4f3ac68b','4065a7d09a026be79ee983da489167f7b49c4aa3bd6306428e8c188da5d75e27') GROUP BY source_key, dataset;
```

[Repair evidence and remaining gaps](/home/ec2-user/data-collection-processing/repair-notes/2026-11-18-entries-91-105/review-status.json).

### q093

**093. China NBS industrial production**

Review (18 November 2026): **reviewed**. SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Exact verified published jobs are selected below; this is a bounded verification sample, not the full inventory. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'china_nbs_industrial_production' AND contract_version = '2.0.3' AND job_id IN ('d949399e0e99badd42244a038f9c4a2c15793b26acaec10fdbf640dcbaab1971') GROUP BY source_key, dataset;
```

[Repair evidence and remaining gaps](/home/ec2-user/data-collection-processing/repair-notes/2026-11-18-entries-91-105/review-status.json).

### q094

**094. China MIIT electronics and battery statistics**

Review (18 November 2026): **reviewed**. SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Exact verified published jobs are selected below; this is a bounded verification sample, not the full inventory. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'china_miit_electronics_and_battery_statistics' AND contract_version = '2.0.3' AND job_id IN ('f8b54541aa44a73d8fff9609aca2b0e99771d0f5927b8998be40a45d06ad9cf7') GROUP BY source_key, dataset;
```

[Repair evidence and remaining gaps](/home/ec2-user/data-collection-processing/repair-notes/2026-11-18-entries-91-105/review-status.json).

### q095

**095. China NEA power statistics**

Review (18 November 2026): **reviewed**. SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Exact verified published jobs are selected below; this is a bounded verification sample, not the full inventory. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'china_nea_power_statistics' AND contract_version = '2.0.3' AND job_id IN ('16c55fc9d1202e5c21cf69566439dc48778e49d916234c6af44a1e8ff94f39e1') GROUP BY source_key, dataset;
```

[Repair evidence and remaining gaps](/home/ec2-user/data-collection-processing/repair-notes/2026-11-18-entries-91-105/review-status.json).

### q096

**096. China NHSA reimbursement and procurement**

Review (18 November 2026): **reviewed**. SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Exact verified published jobs are selected below; this is a bounded verification sample, not the full inventory. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'china_nhsa_reimbursement_and_procurement' AND contract_version = '2.0.3' AND job_id IN ('c33db78dc3b6ef21e8a7475da94212d181b90d60af004cd06097d035fe8a5fd0','058d0e61af1c49f9443c1a3e90ab5d7888ecb8eaed8b131b3219dd528b1f67cf','63b97fa9b878b934ae195af56bcc3006ba0841213ba4eea45f01de319790fb36') GROUP BY source_key, dataset;
```

[Repair evidence and remaining gaps](/home/ec2-user/data-collection-processing/repair-notes/2026-11-18-entries-91-105/review-status.json).

### q097

**097. China MOFCOM export controls**

Review (18 November 2026): **reviewed**. SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Exact verified published jobs are selected below; this is a bounded verification sample, not the full inventory. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'china_mofcom_export_controls' AND contract_version = '2.0.3' AND job_id IN ('9df9ec750abbbb60a6f012edcbc69aca1acfc9e7696930effc6b8e9b37fa139e') GROUP BY source_key, dataset;
```

[Repair evidence and remaining gaps](/home/ec2-user/data-collection-processing/repair-notes/2026-11-18-entries-91-105/review-status.json).

### q098

**098. South Korea FSS OpenDART**

Review (18 November 2026): **partially reviewed — provider document gaps**. Complete native filing-index row paired with its original PDF/XML document; no XBRL fact extraction or historical-vintage inference. Exact verified published jobs are selected below; this is a bounded verification sample, not the full inventory. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[2].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'south_korea_fss_opendart' AND contract_version = '2.0.3' AND job_id IN ('150a6b4af12507f7966a8aa69b94581eb04db6bace4f40ed349b4856aee5cc27','2774856722c5dc550ac0e7c665cada6f18a13661627e8539ea4b083c2bdf79cc','d697b07b2970d227650341b0147f9190b6584a83489e67589543589a0261d282','2b09298bf5497d65a02d78e28fdccf81f5d96bd9bf86beb0b6ce1c65f54b38f3') GROUP BY source_key, dataset;
```

[Repair evidence and remaining gaps](/home/ec2-user/data-collection-processing/repair-notes/2026-11-18-entries-91-105/review-status.json).

### q099

**099. South Korea KOSIS statistical OpenAPI**

Review (18 November 2026): **not reviewed — owner configuration required**. The enabled registry flag was misleading: there is no collector plan, historical route, metadata job inventory or configured KOSIS credential. Owner action: obtain an issued KOSIS OpenAPI key, add it as field kosis to the existing dataSourceAPIkeys-PSTzff secret without replacing other fields, and identify the intended tables/indicators. Do not paste the key into chat. No observations are expected until the key, tables and collector are configured.

```sql
SELECT source_key, count(*) AS observations FROM optima_metadata_engine.source_observations WHERE source_key = 'south_korea_kosis_statistical_openapi' GROUP BY source_key;
```

[Repair evidence and remaining gaps](/home/ec2-user/data-collection-processing/repair-notes/2026-11-18-entries-91-105/review-status.json).

### q100

**100. Taiwan TWSE/MOPS issuer and revenue archives**

Review (18 November 2026): **reviewed**. Native issuer/revenue rows with all returned fields and original reporting month/units. Both complete source arrays (2190 rows) passed raw verification; published proof samples cover 64 rows and continuation remains active. Historical MOPS issuer and monthly-release archive coverage remains unverified. Exact verified published jobs are selected below; this is a bounded verification sample, not the full inventory. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'taiwan_twse_mops_issuer_and_revenue_archives' AND contract_version = '2.0.3' AND job_id IN ('910ea4ceb9af9c8d22b971ec65b03c3d4696e3ff1f6d963a9c2faca746beab74','daea8d65163dda7875efd4d9da3da554ab939d3d0e2e8414ae591e80f0733326') GROUP BY source_key, dataset;
```

[Repair evidence and remaining gaps](/home/ec2-user/data-collection-processing/repair-notes/2026-11-18-entries-91-105/review-status.json).

### q101

**101. Taiwan customs trade statistics**

Review (18 November 2026): **reviewed**. Native monthly aggregate clearance rows, with reporting year and NTD-thousand fields retained. All 153 source rows passed raw verification; published proof sample covers 32 rows, with continuation active. Detailed HS/country trade is outside this feed. Exact verified published jobs are selected below; this is a bounded verification sample, not the full inventory. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'taiwan_customs_trade_statistics' AND contract_version = '2.0.3' AND job_id IN ('4992b7cb101ff6894e12862cd8db19424085e7cd55b27e0329beb1938cafa775') GROUP BY source_key, dataset;
```

[Repair evidence and remaining gaps](/home/ec2-user/data-collection-processing/repair-notes/2026-11-18-entries-91-105/review-status.json).

### q102

**102. India IBM mineral production**

Review (18 November 2026): **reviewed**. SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Exact verified published jobs are selected below; this is a bounded verification sample, not the full inventory. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'india_ibm_mineral_production' AND contract_version = '2.0.3' AND job_id IN ('795e93063ac25a644be02f719b6bc76ed4d961f22b5bf21f2f504dbba1878d2b') GROUP BY source_key, dataset;
```

[Repair evidence and remaining gaps](/home/ec2-user/data-collection-processing/repair-notes/2026-11-18-entries-91-105/review-status.json).

### q103

**103. Indonesia ESDM and Geological Agency mineral statistics**

Review (18 November 2026): **reviewed**. SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Exact verified published jobs are selected below; this is a bounded verification sample, not the full inventory. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'indonesia_esdm_and_geological_agency_mineral_statistics' AND contract_version = '2.0.3' AND job_id IN ('06301c9dbfe37d0a583564920752b025d89187a34a0a7208f24d7faadc5576f2') GROUP BY source_key, dataset;
```

[Repair evidence and remaining gaps](/home/ec2-user/data-collection-processing/repair-notes/2026-11-18-entries-91-105/review-status.json).

### q104

**104. Brazil ANM mineral yearbook**

Review (18 November 2026): **reviewed**. SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Exact verified published jobs are selected below; this is a bounded verification sample, not the full inventory. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'brazil_anm_mineral_yearbook' AND contract_version = '2.0.3' AND job_id IN ('e06be3e6ce704ce4e39344a8c83382672cfa9bd286493e5ce5597bd6dd700b13','c59dd08660326b49c6f764e6fadc933c5edc31fb37041b824035d102d53b2955','26bc455da2d43efb05fdd89eb1acab530893d99b5c42e458883e63e392345af9') GROUP BY source_key, dataset;
```

[Repair evidence and remaining gaps](/home/ec2-user/data-collection-processing/repair-notes/2026-11-18-entries-91-105/review-status.json).

### q105

**105. Brazil ANM CFEM mining royalties**

Review (18 November 2026): **reviewed**. SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step. Exact verified published jobs are selected below; this is a bounded verification sample, not the full inventory. Workgroup: `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = 'brazil_anm_cfem_mining_royalties' AND contract_version = '2.0.3' AND job_id IN ('00ee954f9c6ecfb22ebc61b2673000f29f6a6c5d35cd79075dfcb99d849909e6','62821bcf21536496786b566cf9ae213fa9744a8190071ae636837a20128b0d75','2acaa50d25ee5106103e7d0fdb2707929ab85cd7342e9647ae72f1cb05e5dc6c') GROUP BY source_key, dataset;
```

[Repair evidence and remaining gaps](/home/ec2-user/data-collection-processing/repair-notes/2026-11-18-entries-91-105/review-status.json).

### q106

**106. Brazil MDIC Comex Stat API**

Verified published sample. Workgroup `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original FROM optima_metadata_engine.source_observations WHERE source_key = 'brazil_mdic_comex_stat_api' AND contract_version = '2.0.3' AND job_id IN ('e8df0dde99f1ade0a02fe796f778edff64646f4585fd2bdaca5f443e9f512b4e', '7b85aa0919ee901a238d7403b2998a79aa73b2f778593d026f6a7b094c29a785') GROUP BY source_key, dataset;
```

### q107

**107. Chile COCHILCO production and mining economics**

Verified published sample. Workgroup `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original FROM optima_metadata_engine.source_observations WHERE source_key = 'chile_cochilco_production_and_mining_economics' AND contract_version = '2.0.3' AND job_id IN ('82ee55cd6368a16d7fd6a6789ef0da419015cf1ca0c16b0f8fc11702847a5515', '29692e35b4b1495ec6825ca4ff7d154130d519dd672c2bcd22dfa0deeeba1805') GROUP BY source_key, dataset;
```

### q108

**108. Chile SERNAGEOMIN mining yearbooks**

Verified published sample. Workgroup `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original FROM optima_metadata_engine.source_observations WHERE source_key = 'chile_sernageomin_mining_yearbooks' AND contract_version = '2.0.3' AND job_id IN ('8695365a9694a1f62f3ba902b17c2c2fd50312bc0d3d04d203847cf84e0d0345', 'd942a74e238035e29a8cb096aae080d1ed82e829c2909b36d1ec9abfd2e9e570') GROUP BY source_key, dataset;
```

### q109

**109. Chile SMA SNIFA environmental compliance**

Verified published sample. Workgroup `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original FROM optima_metadata_engine.source_observations WHERE source_key = 'chile_sma_snifa_environmental_compliance' AND contract_version = '2.0.3' AND job_id IN ('af9ae09671940c511d3e3bc4a518f615cfc24a48bc317215cc3030465516136a', 'd86127d8c10b8cd68c2eaa84ac153f79ad30950fd90275b09892450296ce1ce7') GROUP BY source_key, dataset;
```

### q110

**110. Peru MINEM mining bulletins and yearbooks**

Verified published sample. Workgroup `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original FROM optima_metadata_engine.source_observations WHERE source_key = 'peru_minem_mining_bulletins_and_yearbooks' AND contract_version = '2.0.3' AND job_id IN ('df5c3ed777d974df3d418302f26866f3e634fa0fbf9b2036fe29f3e364e01d63', '103b75840ea294bd9e864a5faaa1e6160242bd9cfcf9668cbd884e5a25fd7461') GROUP BY source_key, dataset;
```

### q111

**111. Argentina SIACAM mining indicators**

Verified published sample. Workgroup `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original FROM optima_metadata_engine.source_observations WHERE source_key = 'argentina_siacam_mining_indicators' AND contract_version = '2.0.3' AND job_id IN ('43cd42e19f2f31f8959b214f37364159692ab0b5400db5b68b9b54373785eaa9', '7361533edd13fe9637cadf58b049938f4be79f4047544c1b0dbe47225bf540ea') GROUP BY source_key, dataset;
```

### q112

**112. Brazil ANM SIGMINE and Cadastro Mineiro**

Verified published sample. Workgroup `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original FROM optima_metadata_engine.source_observations WHERE source_key = 'brazil_anm_sigmine_and_cadastro_mineiro' AND contract_version = '2.0.3' AND job_id IN ('91ceb522500404270b28a858991663baa837a6ac830799b138408a0addb44fa3', '5db72aef6dd1afc03364f7ba5f1c04fe6662d2d368dfb4b34bcfc0104e4bdd10') GROUP BY source_key, dataset;
```

### q113

**113. Peru INGEMMET GEOCATMIN**

Verified published sample. Workgroup `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original FROM optima_metadata_engine.source_observations WHERE source_key = 'peru_ingemmet_geocatmin' AND contract_version = '2.0.3' AND job_id IN ('4e1c42ac882cff2a1061d571f3c6e3101c25e139c9113f224c2c231cd6b7b9b8', 'a515a4631e9b4e29e554159c7b0c788e9c0e34246b9b2409f9773c9db6a045a7') GROUP BY source_key, dataset;
```

### q118

**118. US Census International Trade API**

Verified published sample. Workgroup `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original FROM optima_metadata_engine.source_observations WHERE source_key = 'us_census_international_trade_api' AND contract_version = '2.0.3' AND job_id IN ('dab7bbffa21a5522e61aa6766eff59ce9be3bddd9ca1cae9832b1e4fce7a262c', 'ab97940b3f0829f9f6e0ee358d4776053c1069e2963677bd1bf5f96b8a6a69fa') GROUP BY source_key, dataset;
```

### q119

**119. Eurostat Comext goods trade**

Verified published sample. Workgroup `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original FROM optima_metadata_engine.source_observations WHERE source_key = 'eurostat_comext_goods_trade' AND contract_version = '2.0.3' AND job_id IN ('3530641dbab19d3a8f5b9268f8eb058b621be7fe558f98b6b2f38e2a1acc4d28', 'bc731ebfa40fcb4f6b97f81a2568f11bd041c6de0e1332f926272493c2939a1f') GROUP BY source_key, dataset;
```

### q120

**120. Climate TRACE industrial assets and activity**

Verified published sample. Workgroup `optima-collected-data`.

```sql
SELECT source_key, dataset, count(*) AS observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts[1].s3_uri')) AS provider_original FROM optima_metadata_engine.source_observations WHERE source_key = 'climate_trace_industrial_assets_and_activity' AND contract_version = '2.0.3' AND job_id IN ('52e293acf53231481d6c6bca8177fe8ae662370749bb8541000b4d209fa985d5', 'f3e637faa61a5530ed1c88d9b5dc548c524d0176fe7a117b21ebb10d4a22f2f0') GROUP BY source_key, dataset;
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
