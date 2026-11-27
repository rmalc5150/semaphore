# M7 batching

The controller owns the lifecycle through `constellation.m7_lifecycle` and
`constellation.m7_batch`. `optima-m7-shared-autostop.timer` evaluates it every
five minutes under the same lock used by all allowed dispatch paths.

`config/m7-batch-policy.json` controls batching. Initial `catchup` continues
until enabled metadata work, unpublished accepted metadata, and runnable
historical work are exhausted. Blocked jobs and validation failures retain their
evidence for repair; this transition does not mark them successful.

After catch-up, `sleeping` accumulates coalesced service requests on the
controller's persistent EBS volume in `constellation/autostop/m7-batch.json`.
The current policy wakes for 26,000 metadata jobs after at least 19 hours off,
or for any deferred work after 24 hours off. A 130,000-job overflow threshold
can wake the worker sooner to prevent unlimited accumulation.

`running` begins shutdown after five hours, or earlier if all measured queues
and deferred requests are empty. `draining` places
`/opt/constellation/batch-paused` on M7. A systemd condition on `optima-*` and
the historical executor templates prevents new payloads from starting while
existing bounded payloads finish. Long-lived historical executors receive
their normal stop request. EC2 stops only after no relevant active processes
and no `pending.json` checkpoint receipts remain. An SSM or database error
does not authorize a stop. Long payloads can extend runtime beyond five hours.

On wake, the controller clears the marker, restarts enabled historical
executors, and replays deferred requests. Worker timers start on boot and
resume their existing bounded schedules. The historical-only autostop timer
is disabled because it does not account for shared metadata work.

The five-hour runtime is a target, not a capacity guarantee. If daily arrivals
need more processing than fits five hours, overflow runs will occur. Admission
thresholds do not change provider rate gates or job limits.

Inspect `m7-batch.json` and `journalctl -u optima-m7-shared-autostop.service`
on the controller for the current phase, counts, wake reason, and drain proof.
The original lifecycle source is retained in the install backup directory.
To recover from a failed resume, retry the controller timer; running-phase
checks reissue resume so a persisted pause marker is cleared safely.
