# Historical-worker automatic shutdown

The t3 controller checks every five minutes and stops only **i-06241bd1c4e91c2fc (m7i.large)** once the enabled historical capture scope has no healthy unfinished work. Unresolved capture failures are retained for repair and **do not block shutdown**. The existing 24-hour update includes their reasons and evidence, including after m7i stops. No extra email schedule or recipients were added.

Implementation: [check.py](check.py), [proofs.py](proofs.py). The enabled systemd timer is `constellation-historical-autostop.timer`.

## Completion policy

- Every planned raw daily partition from 2016-01-01 through the configured exclusive historical end must be registered. Successful captures and failed captures are accounted for separately; missing/unattempted partitions are unfinished work.
- Successful raw captures need verified manifests. Blocked, retryable-failed and unavailable captures are recorded in the repair list. A quota deferral remains unfinished work.
- Native specialist routes are checked against their actual planned task IDs and saved execution receipts. Healthy partial pagination, discovered/unattempted tasks and quota waits remain work. Failed tasks can be left for repair; a provider-wide failure hold can hand off the source's remaining blocked scopes without claiming they were captured.
- Public routes may finish with failed URLs in the repair list. Unattempted seeds and healthy frontier URLs remain unfinished work. This measures completion of the configured capture route, not complete structured data or every historical vintage.
- Paused, staged, unimplemented and migration-probe routes are excluded explicitly in [armed-scope.json](armed-scope.json). Adding/changing the capture scope requires rearming; it cannot silently reuse the old completion decision.
- The same finished-work condition must be observed for at least ten minutes. Failures and their retry invocations do not reset this completion wait.

The final check serializes with historical dispatch using a MySQL advisory lock. It pauses historical admission only, gracefully stops the worker processes, checks for pending checkpoints/uncommitted RAM files and orphan collectors, rechecks the work scope, writes a durable failure handoff, then calls EC2 StopInstances. It does not terminate the instance or delete EBS/S3 data. t3 daily capture remains enabled.

A pause, idle CPU, an empty queue without registered partitions, or the old backfill deadline is not treated as completion. Inability to verify or persist a checkpoint prevents the stop action so unsaved capture is retained. Capture failures themselves do not keep the worker running.

## Status and repair evidence

- [latest-check.json](latest-check.json): current completion assessment, remaining healthy work and failures.
- [stop-receipt.json](stop-receipt.json): created when shutdown occurs, with checkpoint proof and the failure handoff.
- S3: `research-data/constellation-backfill/monitoring/historical-autostop/latest.json`.
- Daily email input: `research-data/monitoring/health/historical-autostop.json`. The email includes a bounded list and links to the full repair evidence.

Failures remain in their original RDS/S3 records and are not relabelled as success. Repairing them later requires resuming the worker and resetting the affected retry/blocked states as appropriate; rearming does not erase failures or reset their retry controls.

## Commands

Inspect without authorizing a stop:

```bash
cd /home/ec2-user/data-collection-processing
.venv-athena/bin/python -B -m constellation.autostop.check
```

After changing sources, targets or the pinned worker configuration, arm the updated scope:

```bash
.venv-athena/bin/python -B -m constellation.autostop.check --arm
```

The timer uses `--execute`; a manual check without that flag never stops the instance. Arming validates EC2 stop permission with DryRun.

## Verification

63 targeted tests passed. They cover failed raw captures and failed-only URL scopes allowing shutdown, unattempted/quota/pagination work preventing premature shutdown, a successful legacy invocation not proving full completion, the ten-minute observation period, daily repair reporting, exact instance targeting, and checkpoint-drain failure preventing an unsafe stop. The live controller check currently reports `work_remains`, so m7i remains running. The daily digest update was deployed to the existing watchdog and its Lambda update completed successfully.
