# Controller resource-exhaustion incident — October 29–30, 2026

## Established evidence

- The controller is a `t3.medium` with 4,021,923,840 bytes of RAM visible to Linux and no swap.
- The retained kernel journal records a global OOM event at **2026-10-29 11:26:42–43 UTC**.  It was entered by `ssm-agent-worker`; the kernel killed PID 318486, a Python process in `optima-edinet-documents-daily.service`, at 3,529,484 KiB anonymous RSS.  Its cgroup was `/optima.slice/optima-data.slice/optima-edinet-documents-daily.service`.
- The service's normal S3-runtime drop-in limits it to 1,700,000,000 / 1,900,000,000 bytes (`MemoryHigh` / `MemoryMax`).  The host also had `zz-t3-large-memory.conf` installed, overriding that service to 4 / 5 GiB and the enclosing `optima-data.slice` to 5 / 6 GiB.  Those are unsafe limits on a t3.medium and defeat the intended host reserve.
- On October 30 the previous boot's journal ends abruptly at 11:09 UTC.  It contains no new kernel OOM, cgroup-OOM, disk error, hung-task, or sustained CPU/I/O signal.  The 11:00 sysstat sample recorded about 1.8 GiB available, 69.5% idle CPU, and 2.15% NVMe utilization.  It cannot prove the final 9 minutes were healthy.
- Between 10:00 and 11:09 UTC, `constellation-historical-dispatch.service` ran 70 times (normally once/minute), and public daily services ran repeatedly.  The dispatcher repeatedly timed out reading RDS, then exited; when the historical guard was engaged it reported `shutdown_check_in_progress`.  Its 512 MiB limit and observed ~70 MiB resident use do not implicate it as the OOM producer.
- The full stop/start at 11:25–11:26 UTC restored access.  At 11:26:52, before the recovery pause command ran, the historical-dispatch timer automatically started the dispatcher; the recovery then stopped it and the other application timers/services at 11:27.  This is boot-time scheduling evidence, not attribution of the outage.

## Safeguard applied

`optima-data.slice.zzzz-t3-medium-safety.conf` was installed as `/etc/systemd/system/optima-data.slice.d/zzzz-t3-medium-safety.conf` and systemd was reloaded.  The live slice was verified at:

- `MemoryHigh=1700000000`
- `MemoryMax=2000000000`
- `MemorySwapMax=0`

It deliberately leaves the t3.large files intact for the existing hardware-gated resize procedure, but wins on this t3.medium by lexical drop-in order.  No timers or workloads are enabled by this change.

The recovery records show the recorded application timers were enabled and active before the pause; the recovery stopped and disabled them.  The final pre-restart audit found no active Optima/Constellation service or timer, no application unit file still enabled (apart from the inert S3-runtime initializer), no cron files or installed crontab command, and no Docker or Podman executable.

## Controlled restart plan

1. Keep all application timers disabled and collection paused.  Verify `systemctl list-timers 'optima*' 'constellation*' --all` has no active application timer and that no relevant service is active.
2. Verify the live slice values are 1700000000 / 2000000000, then observe `memory.events`, `memory.current`, `free -h`, `df -h`, SSH, and an SSM command for at least 15 minutes with no workload started.
3. Before any one-job trial, verify its effective unit memory cap does not exceed the shared 2,000,000,000-byte slice envelope.  Start only one explicitly approved bounded unit, watch its cgroup and journal, then stop it and review its durable checkpoint.
4. Do not bulk re-enable schedules.  If capacity is required, follow the existing verified t3.large maintenance/resize runbook; only after the instance type and memory checks pass may its t3.large limits be applied.
