# Source failure isolation — October 28

Operating rule: retain a failed scope and its evidence, defer its retry, and continue independent work. A deferred/blocked queue entry describes that job, not permission to stop the collection pool. Missing data remains incomplete until repaired or explicitly reviewed as unavailable.

Implemented:
- Publication discovery catches individual invalid checkpoints and queue-write failures, records durable failure evidence, and continues other checkpoints. Errors are also emitted to the service journal; if S3 logging fails, that failure is printed explicitly.
- Research publication catches group-level failures and continues subsequent groups. A checkpoint inventory failure does not prevent attempting existing publication queues.
- Publication retries now increase from 30 minutes up to 24 hours for repeated failures of the same input. Changed manifest/config inputs reset this retry count. Uncommitted specialist inputs retain the existing 24-hour deferral.
- Historical queue selection prioritizes lower-attempt work, then older updated jobs. The prior query gave retries priority over fresh jobs. Existing per-source concurrency limits, lease fencing and three-attempt parking remain enforced.
- Failed historical jobs release their lease and use increasing retry delays, capped at six hours. Parked jobs retain result/evidence for repair and do not occupy a worker.

Verification: 86 tests passed, including injected checkpoint and publication-group failures while unrelated work succeeds. Tests also check queue exclusion of parked jobs, priority order, lease release and retry bounds. See `tests.log`.

Deployment receipts are retained alongside this file. Publisher changes are installed in the primary checkout and worker copies; subsequently launched processes use them. All 15 historical workers restarted successfully, one at a time, and each was verified active. See `queue-deployment-result.json`. During rollout, 186 bounded jobs succeeded in one observed ten-minute interval (`rollout-progress.json`); this is progress evidence, not a full coverage claim.

Limits: this is not proof that every provider adapter has perfect isolation. Existing bounded invocations still consume some resources before a failure is detected. Shared infrastructure failures (S3/RDS/network) and genuine prerequisite dependencies can prevent affected commits. They must not be bypassed by inventing successful checkpoints or declaring gaps complete. Further investigation of individual provider failures remains in the source-status document.
