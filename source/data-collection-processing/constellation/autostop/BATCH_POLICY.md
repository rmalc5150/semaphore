# M7 batching

The controller owns the lifecycle through `constellation.m7_lifecycle` and
`constellation.m7_batch`. `optima-m7-shared-autostop.timer` runs every five
minutes under the same lock used by all allowed dispatch paths. Running sessions
check for empty queues once an hour. Startup and dispatch recovery, the session
deadline, and drain follow-ups use the five-minute timer cadence.

`config/m7-batch-policy.json` controls batching. The existing worker was
moved out of initial catch-up and into the normal drain and sleep cycle with
unfinished work retained in its durable queues. Blocked jobs and validation
failures retain their evidence for repair.

After catch-up, `sleeping` accumulates coalesced service requests on the
controller's persistent EBS volume in `constellation/autostop/m7-batch.json`.
The current policy wakes after 12 hours off when enabled metadata, historical
capture, publication, or a deferred dispatch needs work. Queue counts are
skipped during this minimum off window.

`running` begins shutdown after twelve hours, or earlier if all measured queues
and deferred requests are empty. `draining` places
`/opt/constellation/batch-paused` on M7. A systemd condition on `optima-*` and
the historical executor templates prevents new payloads from starting while
existing bounded payloads finish. Long-lived historical executors receive
their normal stop request. EC2 stops only after no relevant active processes
and no `pending.json` checkpoint receipts remain. An SSM or database error
does not authorize a stop. Long payloads can extend runtime beyond twelve hours.

On wake, the controller clears the marker, restarts enabled historical
executors, and replays deferred requests. Worker timers start on boot and
resume their existing bounded schedules. The historical-only autostop timer
is disabled because it does not account for shared metadata work.

The twelve-hour runtime is a target. Work that exceeds the daily capacity
remains queued for later sessions. Admission thresholds do not change
provider rate gates or job limits.

Inspect `m7-batch.json` and `journalctl -u optima-m7-shared-autostop.service`
on the controller for the current phase, counts, wake reason, and drain proof.
The original lifecycle source is retained in the install backup directory.
To recover from a failed resume, retry the controller timer; running-phase
checks reissue resume so a persisted pause marker is cleared safely.
