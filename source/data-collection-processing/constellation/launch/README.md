# Historical collection launch — October 26, 2026

Historical collection started at **08:36 CET** (07:36 UTC), following the owner's explicit instruction. RDS collection is enabled. Daily capture and control remain assigned to the t3; the existing daily capture timers remain paused. Controller dispatch, gap audits, health export and daily read-only S3/Athena audits are enabled.

## Running work and capacity

The c7i runs four raw workers and four legacy executors. Its shared systemd slice permits **all 16 CPUs** and caps aggregate worker memory at **28 GiB**, leaving memory for the OS. These are capacity limits, not a claim of 100% sustained utilization. Current collectors are largely network-bound; provider pacing and correctness checks determine throughput. Separate source runtime roots and immutable/private S3 pointers isolate legacy state.

| Enabled source | Historical target / queue | Execution |
|---|---|---|
| USGS earthquakes | 3,951 daily partitions, 2016-01-01 through 2026-10-25 | Raw worker pool |
| NSF awards | 3,951 daily partitions, same dates | Raw worker pool |
| arXiv metadata | 3,951 daily partitions, same dates | Raw worker pool |
| ClinicalTrials | Monthly windows from 2016-01-01 | Dedicated legacy lane |
| SEC filings | Monthly windows from 2016-01-01 | Dedicated legacy lane |
| FDA | Monthly windows from 2016-01-01 | Dedicated legacy lane |
| EMA / CTIS | Requested target from 2016-01-01, actual historical availability subject to audit | Dedicated legacy lane |

Dispatch runs every minute on t3 and coalesces outstanding work. Queue admission targets at most two raw jobs per provider and one for arXiv; concurrent claims can briefly exceed those admission counts. An RDS named lock strictly serializes arXiv HTTP connections across workers; requests retain four-second aggregate spacing. The internal arXiv daily cap is now 10,000 requests rather than 500, with its rate/connection limits retained. This follows [arXiv's API terms](https://info.arxiv.org/help/api/tou.html), which require at least three seconds between requests and one connection. NSF and USGS retain their conservative daily budgets of 1,000 and 2,000 requests respectively; budget exhaustion defers jobs until the next UTC day without consuming failure attempts.

The other 29 staged legacy routes remain gated. This launch does not claim all 158 connectors are operational. Their original credential, quota, publication and federation checks still apply. Existing owner-paused sources remain paused. Original old mutable S3 runtime state is never shared between hosts.

## Verified live progress

At **08:54 CET**, 415 raw daily partitions were succeeded (including the three earlier pilot partitions): 314 USGS, 77 NSF and 24 arXiv. Counts continue changing. The independently read-back USGS manifest and source response passed SHA-256 checks. January 2016 ClinicalTrials contains **1,793 records**, with its requested query's pagination exhausted; collection has continued into 2017. Seventeen completed legacy query windows were present in the checked receipts. This does not establish original historical vintages or full source/year coverage.

See [verification.json](verification.json) for exact counts, source manifests, checksums and the observed queue state. All eight worker services were active, the checkup Lambda code update succeeded, and there were no raw deadlock results from the preceding three minutes. The final tested counts are **76 collector/worker regressions and 54 monitoring/runtime regressions**, all passed. Tests that hydrate frozen universes use an isolated RAM workspace so controller audit cleanup cannot interfere.

## Gap policy and reporting

All attempted missing intervals are recorded. Adjacent or overlapping intervals are merged only within the same source, dataset and scope. Durations use calendar time with exclusive end bounds:

- More than five days: flag for repair/investigation in the existing 24-hour overview email.
- Five days or less: retain the gap without an action flag. Exactly five days uses this stated boundary assumption.
- Unprocessed backlog, healthy bounded pagination and daily quota deferrals are not inferred gaps.

The gap audit runs every 30 minutes. Its current S3 report is `research-data/monitoring/health/constellation-gaps.json`; dated versions are retained under `research-data/constellation-backfill/monitoring/gap-history/`. Raw failures also receive immutable evidence under `.../gap-events/`. The existing email Lambda reads the report and flags only gaps above the threshold. Existing recipients, delivery state and 24-hour cadence were retained; no immediate checkup email was sent for this deployment.

Dedicated core historical lanes continue past a persistently failing window after three attempts, preserving its attempt receipts and accepted-gap list. They never label that accepted gap complete. Page/record limits that resume committed pagination are not skipped under this rule. Daily runner behavior is unchanged.

Known investigation items include FDA February 2016 invalid/missing source dates and failed requests, plus NSF duplicate identities across pages. These remain incomplete and cannot silently become empty or complete. The SEC 2016-Q1 parser failure was traced to one publisher row with an empty company name; the filing is now retained with its CIK/accession and an explicit missing-name marker, rather than dropping the filing or rejecting the entire quarter. An idempotent cleanup fix also prevents an already-removed workspace from turning a verified checkpoint into an invocation failure.

EMA's official [CTIS overview](https://www.ema.europa.eu/en/human-regulatory-overview/research-development/clinical-trials-human-medicines/clinical-trials-information-system-ctis) dates the public system to January 31, 2022. The global target remains 2016; this route does not prove pre-launch public availability. Earlier EU trial coverage and the existing CTIS pagination ceiling require a separate source audit. Pending scans alone are not a date-gap claim.

## API-key progress

The shared secret in `/home/ec2-user/apiKeyRegister.md` contains eight populated fields covering six providers: Comtrade, FRED/ALFRED, Ember, WTO, Copernicus and OpenDART. The worker can read this exact secret; no key values were written into project files or logs. Mapping is in `config/constellation-additional-credentials.json`, with presence-only evidence in [new-credential-presence.json](new-credential-presence.json).

These six new provider connectors still require implementation and authenticated endpoint/entitlement tests. Stored keys do not activate unimplemented integrations. The FDA collector separately has read access to its single existing key secret. Both exact-secret IAM policies are recorded here; no general Secrets Manager access was granted.

## Operator commands

Run on t3 from `/home/ec2-user/data-collection-processing`:

```bash
.venv-athena/bin/python -B -m constellation.control status
.venv-athena/bin/python -B -m constellation.control pause
.venv-athena/bin/python -B -m constellation.gaps
```

Workers are enabled at reboot and consult RDS before collecting. The collection pause prevents further requests and permits checkpointing; it does not shut down EC2. The existing 20-day operational deadline is retained and also does not stop instance billing.
