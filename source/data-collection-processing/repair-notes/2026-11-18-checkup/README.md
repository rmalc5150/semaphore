# November 18 email checkup

The attached overview was dated November 17. Live state was inspected on November 18; recovered service exits were not treated as current stopped workers.

## Repairs verified

- **HKEX:** the original-document validator's 64 MiB ceiling contradicted the official HKEX downloader's 128 MiB allowance. Aligned the validator to 128 MiB, retaining trusted-host/path, PDF-end-marker, empty-body and other validation checks. The October 7 daily replay advanced to 313 committed filings over three pages and ended with `page_limit`, rather than `hkex_original_empty_or_oversize`. This is partial capture, not complete disclosure publication. The previously failing original was 89,270,901 bytes; the residential fallback retains its separate 8 MiB bound.
- **FDA monitoring:** the minimal summary runtime did not contain `research_contract`. Two lazy imports silently prevented committed replacements from clearing retained errors. Canonical task hashing now uses standard-library code with identical serialization. The live worker reconciled the exact May 2025 example successfully. All 54 known repaired monthly windows were rechecked against complete manifests and head terminal histories; 31 merged FDA intervals were removed using a conditional write, with original report and proof list retained. The cached report went from 109 to 78 flagged intervals. This does not certify unrelated historical gaps or publication.
- **ClinicalTrials.gov:** August 2022 restarted after detected source change, continued through committed checkpoints, and completed with exactly 3,290 records over 33 pages. Queued regulatory publication under window `eaf37cc5744309b9d623215023d62bd756b27d6be2fe229e3f3ebace5aa98fa9`.
- **PortWatch:** January 20, 2019 advanced from the old invalid-response failure to 2,000 rows, then completed at 2,071 records. Exact task identity was preserved and specialist publication queued.
- **Census:** the October 2026 replay now explicitly returns `census_period_not_yet_published`. This is an incomplete release-lag window, not an evidenced permanent exclusion.
- **TED:** added a narrow fresh-generation recovery for failed resumed iteration tokens with count mismatch/missing iteration page. First-page failures, unrelated HTTP errors and healthy partial runs do not trigger a reset. Counts are not relaxed, old manifests are retained. November 2016 live replay committed 200 records and ended at its two-page allowance.

## Publication and services

Only three of the 54 repaired FDA windows had verified publication receipts at inspection. The other 51 remain queued. A bounded worker continuation, `optima-fda-repair-publication-20261118.service`, waits on the existing publication lock and processes three-window batches, releasing the lock between batches. It has a 30-minute runtime bound, 1,200 MiB memory ceiling and 25% CPU allowance. Its log is `/opt/constellation/tmp/checkup1118/fda-publication.log`; per-batch outcomes are saved under `research-data/constellation-backfill/repairs/2026-11-18/fda-publication-*.json`. This pass does not claim those 51 windows, the new ClinicalTrials window or the new PortWatch scope are Athena-verified.

Previously reported assignment/CMS/FDA/NIST exit failures have successful latest service results. NIST currently reports `waiting_for_completed_S47_capture_today`, which is a dependency wait, not proof of a new completed capture. All 15 worker executors were active at the final check; the metadata streaming timer was active. No healthy collector was stopped for these repairs.

## Still unresolved

- Finlight November 17 still detects changed pagination in a later component scope. The normal controller service was run through its configured credential route; three earlier scopes remain complete. Existing per-day refresh and request budgets were preserved. An exploratory worker invocation was denied access to `newKeys`; this is not the configured controller route, and no secret permission was expanded.
- HKEX October 7 and subsequent dependent disclosures need continuation, publication and readback.
- Market health still reports 174 daily / 201 historical unresolved symbols, with 56 reviewed exclusions. No new blanket exclusions were added.
- EMA, DataCite, Zenodo, WTO, NHSBSA, USAspending, UNIDO, other EDINET and weather groups still require individual diagnosis/replay. The separately requested full historical audit exceeded its 600-second diagnostic limit (`refreshed-gaps-result.json`); it did not produce a new full report. Its runtime/query cost remains engineering work. The targeted FDA reconciliation is independently verified.
- MHRA's current official Innovation Passport list has eight rows containing company, product and indication, but no designation-date column. Saved probe: `research-data/constellation-backfill/repairs/2026-11-18/mhra-current-list-probe.json`. Undated current lists cannot establish historical designation dates. Historical exclusion design must distinguish these rows from dated orphan-register observations; no blanket history completion was asserted.

## Owner actions

No new credential, purchase, persistent permission change or manual restart is requested by these findings. Continue reviewing already verified Athena samples and report missing specialist fields. Newly queued batches need engineering publication/readback before owner review. SMS remains working. EDINET 2016 stays excluded; Reddit, Bluesky, GitHub source capture and Marketaux remain paused.

## Validation and evidence

`tests.log`: 34 relevant regression tests passed. Worker deployments used backups, atomic replacement and compilation. `*-command.json` / `*-result.json` retain bounded SSM step outcomes. `monitoring-reconciliation.json` records exact FDA proofs and backup location. `clinicaltrials-finish-result.json`, `portwatch-finish-result.json`, `ted-recovery-result.json` and `hkex-replay-result.json` contain live outcomes.

One intermediate ClinicalTrials replay encountered a conditional-write conflict only when writing its repeated repair-note key, after the collector checkpoint had already committed. Subsequent notes use unique keys; canonical state confirmed 3,000 records and the next continuation finished at 3,290. No captured rows were deleted or bypassed.
