# Isolated repair replays — 21 October 2026

## Failure diagnosis

The original `optima-repair-core` and `optima-repair-verify` jobs both exited 120 at 20:49:07 Europe/Madrid. Their recorded launch commands used `systemd-run --wait --pipe`; worker output was not retained in the journal. No kernel OOM event was recorded in the inspected interval. A controlled closed-stdout-pipe test reproduced Python exit 120 and BrokenPipeError. This strongly supports output-pipe disconnection as the common failure; the original worker traceback was not retained, so it is not conclusively proven.

## Changes

- Replacement service is detached, without `--pipe` or an interactive terminal dependency.
- Each step writes its own persistent `.log` and atomic `.json` result here.
- Each step has a bounded execution allowance, graceful interrupt before forced termination, and its own S3 runtime checkpoint.
- The sequence stops if checkpoint verification is missing. A failed source step with a verified checkpoint does not hide the next step.
- A zero process exit means execution completed, not that historical coverage is complete. Capture and Athena results are separately recorded.
- Fixed repair-report updates to use conditional S3 replacement and retain immutable attempt records. This was exposed by the Europe PMC replay after its capture and Athena verification had succeeded.
- Reddit, Bluesky and GitHub are excluded. At exit the runner restores only timers active at maintenance entry, provided no uncheckpointed state remains.

## Evidence

`summary.json` and the per-step logs record execution and checkpoints. `athena-receipts.json` independently checks publication receipt hashes and actual Athena query states. The first PMC process exit remains recorded as failed because its report write failed; its separate Athena receipt confirms the data was published successfully.

Completed at approximately 22:49 Europe/Madrid. A successful bounded replay does not imply the entire archive is complete.

## Verified results

| Repaired scope | Athena result |
|---|---|
| Europe PMC full text | 1 record; original API failure recovered through validated official PMC fallback |
| CAISO | 120 records; legacy scope migrated after verified publication |
| SAM.gov | 143 records |
| USPTO assignment history | 1 record |
| MLPerf | 2 records |
| EIA retail prices | 1 monthly observation |
| EIA generator inventory | 1,826 records from the August 2026 workbook; later unpublished periods explicitly deferred |
| MHRA | Three windows, 263 records each |
| HKEX disclosures | 30 disclosures |

Fresh SELECT * samples verified actual fields for the first seven specialist sources. Core publication receipts verify the MHRA and HKEX table counts. These records retain existing source/coverage and entity-linking limitations.

The shared `optima_collected_data.observations` publication verified 78,452 new observations in the first pass and another 2,147 in the final pass, including the final 1,826 EIA generator records and 200 patent records. The catalogue contains 86 source/dataset partitions and 16,007,029 committed observations, including historical versions and incomplete windows; this is not a count of unique entities or complete archives. Both passes checked counts and required identifiers and saved their checkpoints.

## What remains

- Marketaux daily capture: changing provider result set remains unresolved. Historical requests reached the daily budget; no budget bypass was attempted.
- USPTO daily capture: the resumed partition moved past the source-change failure and committed another 200 records; it stopped at the configured page limit. The day is still incomplete.
- USPTO office actions: source-change cooldown remains active. Petition decisions reported caught up through the configured completed-day boundary.
- Historical backlog and previously documented market coverage gaps remain separate work. No new credentials or hardware purchase was established as necessary by these replays.

## Runtime and validation

All 66 timers active before this maintenance session are active again. Maintenance is cleared. Reddit, Bluesky and GitHub's four dedicated timers remain disabled; collector guards remain in place. A live CAISO backfill started after restoration, so a normal in-flight runtime marker may be present.

All initial, follow-up and final repair steps verified their runtime checkpoints. Eight focused runner/report/publication regression tests passed. The three detached supervisor services completed successfully; individual provider failures and intentional interruptions remain visible in the step reports rather than being relabelled successful.

No action is required from the user for the repaired execution/logging mechanism. The remaining provider conditions and incomplete scopes are not claimed fixed.
