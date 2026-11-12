# Personnel announcement archives — November 9, 2026

## Verified results

Personnel announcement archives (`personnel_archive`) is marked reviewed after validation and publication checks. The IDE-selected `clinicaltrials_gov` query concerns a separate source; that review was not changed.

- Metadata Athena query now returns **nine raw-complete observations / five linked raw batches**, latest ingestion November 9 at 17:07 UTC. Query `7f68786a-d8ed-468c-9aff-9ed8828226d4`.
- Fresh archive capture consumed one repaired RSS record and committed one derived personnel-source candidate with zero undated/before-floor skips.
- Curated `optima_people_research.source_observations_windows` verified the record, `capture_status=captured`, its nested **1,958-character** article body and the full-content S3 reference. Query `1c349958-d94a-4096-8d9e-48513f380301`.
- All four previously failed batch slices passed original-content/lineage validation and production replay. **37 focused tests passed.**

These are checked scopes, not a complete historical corpus or confirmed personnel events.

## Root cause and repair

Archive entries are derived wrappers around upstream collected records. The generic metadata contract had no applicable host allowlist and did not follow `payload.data`, parent manifests/batches, or the nested original-content evidence. It therefore stopped after four missing-provider-record failures despite saved upstream article material.

New immutable contract `2.0.3` requires the collected provider envelope, verified committed parent record and substantive source-content evidence. The validator checks archive/parent observation IDs, parent record ID, article URL, the archive-pinned parent-manifest checksum, complete/exhausted parent manifest, committed head, batch checksum and exact parent-record equality. It then validates upstream article or original-document content. Unsupported/missing evidence remains an explicit record-level gap rather than an excuse to publish an index/URL as complete.

The original parent record, source text and source candidate annotations remain intact. The owner review does not change `unreviewed_source_candidate` into a verified movement or resolve legal-company identity.

Preserved failure reports and superseded/requeued 186 old-version jobs under the new contract. Production replay accepted eight earlier records plus one fresh capture. Further jobs remain queued. Missing parent content is recorded in `pipeline_failures` (`personnel_archive_content`) and job reports while other records continue. Reviewed-source date-queue mode is installed locally, remotely and in installation defaults.

## Infrastructure check

Daily and historical collection controls permit work. All 15 historical workers are active (five native, six legacy, four public). Metadata timers are enabled, and fresh accepted jobs were observed for CAISO, SAM.gov, HKEX, WTO and FRED. Existing people capture/research-publication schedules are retained.

The worker's failed-unit list is empty after clearing only old transient verification flags whose repairs had already succeeded. Journal evidence remains. The separate controller `ec2-code-backup.service` remains failed; it is not a collection/metadata service failure.

Final source states: **73 enabled, 75 raw-stopped, five owner-paused, four access-layer**. **2,137 accepted metadata batches await publication** at the final snapshot. Those other source-specific holds are not waived. Online schedules do not prove all sources healthy or all history complete.

No new owner credentials, purchase or access action is needed for this archive repair. Continue normal per-source content reviews and monitor backlog publication. ClinicalTrials.gov is separately raw-stopped and has not been marked reviewed by this task.

## Evidence

`tests.log`, `failed-batch-validation.json`, metadata deployment results, `migration.json`, replay results, `fresh-capture.json`, `athena-verification.json`, `curated-payload-verification.json`, `review-policy-result.json`, worker/controller evidence, `final-status.json`.
