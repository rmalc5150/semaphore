# Historical migration status — October 26, 2026

**Current update:** Historical collection was explicitly released at 08:36 CET on October 26. Eight c7i worker services are active; three raw sources and four dedicated core lanes are enabled. The earlier paused-state verification below is retained as setup evidence. See [live launch status](../launch/README.md).

Historical execution targets the c7i worker `i-06241bd1c4e91c2fc`. Daily capture, scheduling and control stay on the t3 controller `i-070bab0b09f794629`. All 158 catalog entries now declare this placement in the local and RDS registry. Placement does not imply that a connector is implemented or ready.

## Installed routing

24 existing historical systemd services on t3 now dispatch fixed, validated job specifications to the existing RDS MySQL queue instead of running collector payloads locally. Five mixed services retain their original runtime guards but run daily-only commands on t3; their historical commands have separate c7i routes. The historical source-schedule controller remains on t3.

The c7i runs two raw-adapter workers and one sequential legacy executor. Legacy workspaces have separate RAM roots and S3 runtime pointers seeded from a frozen verified checkpoint. Native raw, manifest and task identities are preserved. The executor verifies its private durable checkpoint before reporting invocation success. Pause checks run every five seconds between bounded work; interrupted work must preserve its checkpoint before further work.

## Verified collection and current pause

A real existing ClinicalTrials collector ran on c7i for the requested January 2016 window and wrote 100 records. One raw object, its SHA-256 and the final manifest were independently checked. The source status is **partial**, reason `page_limit`; pagination was not exhausted. This is migration evidence, not complete January or historical coverage. See [pilot verification](clinical-pilot-verification.json). Three earlier new-adapter pilots verified another 702 records.

Final readback confirms all three worker services active and idle, zero active queue leases, an empty pilot allowlist, collection disabled, and all 74 Optima timers disabled. No collection was resumed. See [final verification](final-verification.json).

## Access and remaining gates

The owner-approved artifact policy is applied and was read back exactly. It permits the documented native artifacts; hashed old checkpoint paths can also reach daily task checkpoints, so fixed commands and mode separation enforce ownership. No source-secret permissions were added. See [access review](ACCESS_REVIEW.md).

All 29 normal historical routes remain execution-disabled pending their listed checks. Shared per-provider HTTP pacing is installed, but it does not replace weighted, hourly or daily vendor budgets. Remaining work includes EODHD weighted quotas, SAM budget ownership, Google federation for the new role, specific source-secret grants, publication/notification separation and source-by-source validation. Existing source pauses remain in force. New source integrations still need implementation and rights/coverage audits.

## Route gates

| Historical route | State | Remaining requirements |
|---|---|---|
| `optima-authenticated-historical.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review, shared_sam_budget_migration |
| `optima-bls-enrichment-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review, publication_and_notification_separation |
| `optima-caiso-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review |
| `optima-cms-financial-collection.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review, publication_and_notification_separation |
| `optima-core-historical.service` | Staged; disabled | per_provider_quota_and_entitlement_review, explicit_access_to_FDA_and_Decodo_secrets, remaining_core_source_validation |
| `optima-doe-storage-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review |
| `optima-edinet-document-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review |
| `optima-eia-enrichment-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review, publication_and_notification_separation |
| `optima-federal-register-enrichment-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review, publication_and_notification_separation |
| `optima-finlight-content-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review, publication_and_notification_separation |
| `optima-grant-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review |
| `optima-hkex-document-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review |
| `optima-marketaux-content-backfill.service` | Staged; disabled | operator_paused, publication_and_notification_separation |
| `optima-mlperf-enrichment-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review, publication_and_notification_separation |
| `optima-nist-robotics-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review |
| `optima-nmpa-enrichment.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review, publication_and_notification_separation |
| `optima-patents-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review, google_federation_new_worker_role |
| `optima-people-content-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review, publication_and_notification_separation |
| `optima-pubmed-enrichment-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review, publication_and_notification_separation |
| `optima-regulatory-enrichment-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review, publication_and_notification_separation |
| `optima-s11-content-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review, publication_and_notification_separation |
| `optima-specialist-historical.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review |
| `optima-ted-enrichment-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review, publication_and_notification_separation |
| `optima-usgs-minerals-backfill.service` | Staged; disabled | dependency_and_workspace_validation, per_provider_quota_and_entitlement_review |
| `optima-market-collection-historical.service` | Staged; disabled | split_lane_regression_and_runtime_validation, distributed_weighted_eodhd_quota |
| `optima-news-collection-historical.service` | Staged; disabled | split_lane_regression_and_runtime_validation |
| `optima-conference-collection-historical.service` | Staged; disabled | split_lane_regression_and_runtime_validation |
| `optima-people-collection-historical.service` | Staged; disabled | split_lane_regression_and_runtime_validation |
| `optima-patents-prosecution-historical.service` | Staged; disabled | split_lane_regression_and_runtime_validation |

## Validation

58 collector/routing regressions and 43 storage/runtime regressions passed in separate processes. Storage tests install their own filesystem hooks; a combined run with startup hooks enabled produced one test-harness conflict, resolved by running that suite with startup hooks off. No full-suite pass is claimed; the earlier two PubMed parser fixture failures remain outside this change.

Executor bootstrap/verifier failures are retained as blocked/superseded diagnostic evidence, separately from source availability. Successful bounded invocations never mark source/year coverage complete.

## Operator commands

Run on t3 from `/home/ec2-user/data-collection-processing`:

```bash
.venv-athena/bin/python -B -m constellation.control status
.venv-athena/bin/python -B -m constellation.control pause
```

Worker services start idle at reboot. Do not use bulk `resume` or enable timers until the relevant route gates are cleared and collection is intentionally released. The operational deadline pauses work but does not stop EC2 billing.
