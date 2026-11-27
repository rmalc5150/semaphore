# High inspection alert — November 20

The alert's exact detail was:

`Batch verification cache not persisted: [Errno 30] Read-only file system: '/home/ec2-user/data-collection-processing/state/tmp5p3yr2gk'`

First observed at **14:05 CET**; still active at **14:35 CET**. This was an optional monitoring-cache write failure, not evidence that the collection workers or Athena data had failed. Actual source/pipeline findings remain separate.

The health service uses `ProtectSystem=strict`, marks the home/workspace read-only and had no writable paths. Its new batch-verification cache attempted an atomic temporary-file write under `state/`, which the service sandbox prohibited.

The cache now uses `state/collection-health/health-verified-batches.json`. A narrowly scoped systemd drop-in allows writes only to that dedicated directory; the rest of the monitor's read-only sandbox is retained. No IAM/API permission or collection schedule was changed. The actual service was rerun inside its normal systemd sandbox.

Evidence: `alerts.json` / `health.json` are the original S3 snapshots; `health-after.json` records the verification run. The exact drop-in is `health-cache.conf`, installed as `/etc/systemd/system/optima-collection-health.service.d/zzzzzzzzzzz-health-cache.conf`.

Owner action: **none**. No new key, purchase or manual restart is needed.

## Verification

The actual sandboxed service completed with `Result=success`, exit status 0. Its fresh health report (14:38 CET) contains **no monitoring errors**, and the 16,757-byte cache file was successfully written in the dedicated directory. The high `monitor:inspection_failed` incident was reconciled against that report with notifications disabled; see `reconciliation.json` and `alerts-after.json`. Collection workers were not restarted, and unrelated source incidents were retained.
