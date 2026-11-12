# S48 MLPerf evidence enrichment

The daily MLPerf summary collector attaches commit-pinned system descriptions,
measurement settings/README files, accuracy reports and LoadGen performance
summaries to each result under `payload.data.enrichment`. Source units, model,
scenario, accuracy and power availability remain unchanged. Original downloaded
files, SHA256 receipts and source evidence are stored in S3; enrichment includes
source content, paths and Git blob hashes. Nothing is executed from submissions.

Capture is scoped to the tested system and model/scenario. Files above 512 KiB or
above the 2 MiB per-result capture budget remain indexed with explicit gaps; full
model weights, predictions, datasets and arbitrary source code are not collected.
Git tree enumeration falls back from truncated recursive responses to smaller
subtrees. When the directory API is rate-limited, official immutable raw URLs for
standard system/configuration/accuracy/performance paths remain usable. These
records explicitly report `standard_paths_api_deferred`; their computed Git blob
hashes are not represented as independently checked directory entries. Missing
roles and incomplete inventory remain review-required even when core files exist.

Daily snapshots pin the commit and summary blob in their cursor, process at most
50 result rows or approximately 8 MiB of payload per page, and retain durable page
checkpoints. Source record IDs preserve the existing composite identity. Daily
collection now checks the four most recent configured editions (currently v5.0,
v5.1, v6.0, v6.1) rather than relying solely on the final configured edition;
unavailable repositories remain visible failures, not proof of zero results.
The configured historical repository list is unchanged. Existing independent
artifact jobs remain supporting evidence; they are not benchmark events.

Daily task scopes/version changed for MLPerf to ensure old completed summary-only
tasks cannot suppress enriched collection. The current daily timer runs hourly
with the existing job fairness and resource limits. GitHub's shared public API
budget remains in force; the raw-file fallback avoids using that API for every
artifact. Immutable file caching reuses evidence across results and runs. A
captured cached artifact retains its original retrieval evidence; no historical
availability is inferred.

Backfill config: `config/mlperf-enrichment-backfill.json`. Its hash-pinned inventory
covers 344 committed S48 batches / 24,014 observations present at setup. Distinct
source/result content and commit versions are retained; repeated captures are
grouped. Parent observation/batch lineage, original dates and unresolved entity
IDs are preserved. Supporting artifacts are marked separately from result rows.
Outputs are new immutable observations, never in-place edits to historical rows.

The enabled `optima-mlperf-enrichment-backfill.timer` resumes bounded work every
five minutes. Retries are bounded per record; API quota deferrals do not consume
record retry attempts. Raw evidence and job state are archived under existing
S3 collection storage. Local status:
`reports/mlperf-enrichment-backfill-2026-10-18-latest.json` and the matching SQLite
registry. Durable state/receipts:
`operations/mlperf/enrichment-backfill/mlperf-enrichment-backfill-2026-10-18/`.

Completion email goes to the established confirmed recipient
randall@optima-holdings.com only after every pinned version has an output and the
exact job output counts are verified in `optima_collected_data.observations`.
The email includes counts and a gap/review receipt. `finished_with_gaps` means
processing finished with explicit limitations, not complete evidence coverage.

Live verification for submission 5.0-1553 at commit
0bc17ab3f4b33f730d7869e04cc29cb70835e513 captured five files: system JSON,
user.conf, measurement README, accuracy.txt and mlperf_log_summary.txt. GitHub's
API was rate-limited, so the standard-path fallback was used and flagged.
See `reports/mlperf-enrichment-live-verification-2026-10-18.json`.

The payload includes role-separated entity candidates, a stable benchmark event
candidate key/content version and comparison context. These are pending-review
inputs. **RDS matching, automatic registry writes/admission, main event-ledger
integration and specialist execution are not enabled by this change.** Their
required workflow and acceptance criteria are recorded in `ENTITY_DISCOVERY_ROLLOUT_PLAN.md#event-pipeline`.

Validation:
`python -m unittest test_mlperf_enrichment test_mlperf_enrichment_backfill test_specialist_inputs -q`.
