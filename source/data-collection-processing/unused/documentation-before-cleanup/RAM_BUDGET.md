# RAM audit and active 4 GB operating budget

September 24, 2026. The budget was installed after the audit, with user authorization. It is not an assertion that all jobs have been load-tested on a 4 GB instance. All 14 original jobs were resumed at the user’s request; conference publication is enabled under its 768 MiB cap. A fifteenth job now collects personnel sources every 30 minutes under a 256 MiB cap.

## Initial snapshot before caps and restart

- Host physical RAM: 8.20 GB (7.64 GiB). No swap.
- Non-free memory: 2.66 GB, including approximately 1.18 GB of cache/buffers/reclaimable slab. Cache is reusable and should not be mistaken for an unreclaimable application requirement.
- MemTotal minus MemAvailable: 1.78 GB. This is an estimate of pressure-relevant usage, not a guarantee of future demand.
- Research publisher: 571 MB current cgroup usage; 632 MB recorded peak for that invocation. At the snapshot, its anonymous memory was 444 MB and file cache 123 MB.
- Development tools/editor: approximately 906 MiB combined proportional set size (PSS). PSS avoids double-counting shared pages; some root processes could not be measured this way.
- Conference full-window local curation benchmark: 98,408 records, 216.28 MiB peak RSS. Separate observed cgroup peak was about 370 MiB including file cache. Publication was stopped at this initial snapshot.
- Journal review confirmed two conference-publisher global OOM kills. SIGINT exits for other services are not counted as memory failures.
- Thirteen of fourteen configured jobs have unlimited MemoryMax. Inactive jobs have unknown peak memory, not zero requirements.

## Every configured job

| Job | Assessment | Basis / next measurement |
|---|---|---|
| `optima-collection-daily.service` | heavy/unmeasured | Mixed regulatory, filings and document paths; whole-document buffers and source-dependent batch sizes. |
| `optima-conference-collection.service` | bounded/unmeasured peak | 500-record pages; source JSON and normalized page coexist. One daily and one historical window. |
| `optima-conference-publication.service` | heavy/measured; resumed | Streaming curation benchmark: 216.28 MiB process RSS; installed hard cap 768 MiB. Full live upload peak not yet benchmarked. |
| `optima-eodhd-profiles.service` | heavy/unmeasured peak | Profile planning loads each prior cohort; inventory symbols retained; fetch workers=4. Needs streaming planning and a measured large cohort. |
| `optima-market-collection.service` | bounded/unmeasured peak | Per-symbol yearly price/action windows; repeated bounded work in a single invocation. |
| `optima-market-publication.service` | heavy/unmeasured peak | Whole-window raw records, normalized rows and Arrow copies; one annual symbol small, HKEX daily window larger. |
| `optima-news-collection.service` | bounded/unmeasured peak | Provider page and HTTP budgets; raw response and normalized records coexist. |
| `optima-news-publication.service` | heavy/unmeasured peak | Whole-window aggregation and multiple in-memory tables. |
| `optima-nmpa-inventory.service` | bounded/unmeasured peak | Rendered page capture; checkpoint record-ID sets accumulate; detail cohorts have separate materialization. |
| `optima-patents-backfill.service` | heavy/unmeasured peak | Export ingestion batches plus growing identity sets; needs a full monthly run measurement. |
| `optima-patents-daily.service` | heavy/unmeasured peak | Patent ingestion workload varies by source package. Do not infer peak from idle/budget-exhausted runs. |
| `optima-patents-global-monitor.service` | light/unmeasured peak | Metadata observation only; no full BigQuery export. |
| `optima-patents-publication.service` | heavy/high-priority fix | Whole-month read_inputs, row list, Arrow table and full Parquet read-back; same growth pattern as old conference curator. |
| `optima-people-collection.service` | bounded; first two runs successful | Sequential feeds, archive scan and people publication; 256 MiB cap. |
| `optima-research-publication.service` | heavy/measured current cycle | Observed cgroup peak 631,869,440 bytes; other cohort sizes and source groups remain unmeasured. |

## Installed data-job envelope and host allocations (decimal GB)

| Allocation | Budget |
|---|---:|
| All data-job processes and their cgroup-charged cache combined | 2.0 GB |
| OS, SSH/SSM, editor and development tools | 1.4 GB |
| Additional cache, transients and safety reserve | 0.6 GB |
| Target capacity | 4.0 GB |

All 15 data services now use optima-data.slice with a 2,000,000,000-byte aggregate ceiling and 1,700,000,000-byte reclaim threshold. This caps only managed jobs, not the whole host. Other programs and root-charged cache remain outside it. Do not impose a host-wide cap that could kill SSH or the editor.

Thirteen heavy services now share an exclusive flock lock. The global-patent metadata monitor and bounded 256 MiB people worker run outside that lock, still inside the shared memory slice. Their combined caps plus the largest heavy job and 64 MB of wrapper allowance remain below 2 GB. Offset timer minutes alone is insufficient: jobs run for variable durations and can overlap subsequent slots. Retain independent light-job capacity only after its measured peaks fit the envelope. Admission control should defer work before starting, rather than relying on OOM termination.

The caps now protect the host. Remaining validation/optimization: stream patent publication and remaining large research/profile curators; stream historical-profile planning; benchmark representative full source windows and live upload paths under per-job caps; measure aggregate overlap and host overhead. Caps without these changes can protect the host while repeatedly failing collection jobs.

At 21:12 UTC the host reported 3,835 MiB total RAM and 2,228 MiB available. At 21:13 UTC the data slice used 675,315,712 bytes with a 2 GB ceiling and no failed systemd units. These are snapshots, not full-day peak guarantees. Linux may use otherwise free memory as reclaimable cache.

## Ongoing observation

`job_memory_audit.py --duration 3600 --interval 5` is observing normal cgroups for one hour, without launching/stopping jobs or reading API credentials. It atomically updates `reports/ram-observation-2026-09-24.json`. That report distinguishes observed concurrent demand from each job’s independently observed peak. Short jobs between samples and overnight/next-day jobs can be missed; an hour cannot establish all daily maxima.

Initial detailed snapshot: `reports/ram-audit-2026-09-24.json`. A complete 24-hour observation and representative backfills are still needed to validate the proposed envelope.

## Deployment and queue behavior

Six timer offsets changed without increasing collection frequency. Thirteen
previously active timers were restored after the two running market jobs were
interrupted for checkpointed restart under the new slice. Conference publication
was initially excluded; it was subsequently enabled and started when the user requested all jobs resume. During verification, GNU timeout's
minute syntax was corrected from `45min` to `45m`; wrapper duration parsing is
now tested for every service. The two interrupted jobs were resumed.

Queue wrappers wait up to six hours for the shared lock, using little memory.
Once admitted, GNU timeout applies each job's original execution deadline and
sends SIGINT, then forces termination after a further 120 seconds if necessary.
The systemd outer deadline is 13 hours, covering queue wait plus the longest
six-hour job. Lock expiry returns 75 and is treated as deferred, not a source
completion; collection checkpoints do not advance and the next scheduled
invocation retries. Daily jobs may therefore be delayed until the next daily
invocation if the queue stays saturated. FIFO fairness is not guaranteed by
flock; queue latency and backfill throughput need observation.

Per-job limits range from 201 MB for the metadata monitor to 1.4 GB for patent
publication, with limits below the aggregate envelope. Limits include each
job's charged filesystem cache. An OOM-limited job can fail rather than finish;
this protects the host but does not solve an unbounded algorithm. On such a
failure, inspect checkpoints and optimize or reduce the cohort rather than
raising the aggregate cap automatically.

Run collectors through their systemd services. Direct CLI/manual processes
outside this slice bypass both the shared lock and these memory limits. The
OS/development allocations are budgets, not enforced host-wide cgroup caps.

`config/ram-budget.json` contains the deployed caps; service and timer drop-ins
are versioned under `systemd/`. `reports/memory-budget-deployment.json` records
the handoff. Two policy/locking tests passed, including execution of each
configured timeout duration against a harmless command. Systemd verified all
units. Live inspection confirmed one executing heavy Python process and other
heavy services holding only waiting flock processes; a competing lock request
returned the expected 75.

The capped read-only `optima-budget-observation.service` records the next hour
of live usage in `reports/ram-budget-live-observation.json`, including jobs in
the new slice. Conference publication is now resumed.
