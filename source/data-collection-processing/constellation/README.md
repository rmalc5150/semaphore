# Constellation collection rollout — October 26, 2026

**Daily capture update:** 33 daily capture/publication timers are now resumed on t3; the c7i pool has five raw workers and four legacy executors (nine total). See [the complete source status report](../../data-source-status-2026-10-26.md) for all 158 entries, live Athena checks, publication gaps and SQL.

**Collection is now running:** At the owner’s request, historical collection started October 26 at 08:36 CET. Eight c7i worker services can use all 16 CPUs under a 28 GiB aggregate memory limit. The 2016 target is registered for USGS, NSF and arXiv, with dedicated SEC, ClinicalTrials, FDA and EMA lanes. Provider limits still apply. Daily capture remains assigned to t3 and its existing capture schedules remain paused. Controller dispatch, gap audits and read-only health monitoring are active. See [launch status](launch/README.md); older paused-state statements below describe the initial setup.

The permanent controller is `i-070bab0b09f794629` (`t3.medium`). The already-created historical worker is `i-06241bd1c4e91c2fc` (`c7i.4xlarge`). Existing Optima timers remain disabled during this rollout.

## Operational design

At the owner's request, the existing encrypted RDS MySQL instance hosts a separate `constellation_operations` schema. No DynamoDB or SQS resources are used. InnoDB rows form the durable queue: transactions with `FOR UPDATE SKIP LOCKED` claim jobs, expiring leases recover interrupted work, and random lease tokens prevent an old worker from committing after reassignment. Two worker processes are the initial limit because the shared database is a `db.t4g.micro`; benchmark database load before increasing concurrency.

Controller and worker have separate database users and Secrets Manager secrets. The worker cannot enable collection, register partitions, alter their specifications, or read the existing `tracking` application tables. Its dedicated IAM role permits the worker secret, the new S3 backfill prefix, SSM management, worker log writes, three immutable seed snapshots and the separately owner-approved native legacy artifact policy. No source-secret access was granted. The dedicated IAM role is installed and verified: the worker cannot read the legacy S3 runtime checkpoint or the RDS master secret. The controller never grants permissions to its own role.

The worker has a separate encrypted 8 GiB gp3 volume mounted at `/opt/constellation`. This minimum-size volume holds the measured small code/runtime installation; responses are bounded in RAM and written directly to S3. The existing 100 GiB root volume is unencrypted and is not used for raw evidence or static credentials. Secrets remain in memory. Scratch is not the authoritative checkpoint store.

## Historical scope and gaps

The shared historical floor is now `2016-01-01`, including original hardcoded conference/personnel filters and the explicit core systemd origin. Daily origins are preserved. Existing captured data, checkpoints, verified entitlement boundaries, and immutable enrichment input snapshots are retained. Frozen 2021-era enrichment inventories describe their original cohorts; the expanded target does not pretend those inventories contain 2016 records.

`config/collection-gap-policy.json` permits documented gaps while unrelated jobs progress. Failures get bounded retries and then remain blocked/partial. Permanent unavailability requires a source, interval, reason, evidence URI and review timestamp. Missing values are not zero. A successful query means only the requested query's pagination was exhausted; it does not establish original vintages, complete fields, or complete source/year/geography coverage.

The registry preserves all 158 supplied catalog rows, their original keys where established, four source pauses, and access-layer distinctions. The matrix contains 1,738 source/year cells. Three 2016 cells now contain one-day pilot evidence and remain partial; the others are unaudited. No complete-year coverage is claimed. There are 64 existing catalog entries and 94 additions. The scheduler's older 68 operational routes have a different granularity and must not be equated with 68 independent publishers.

The first isolated adapters are USGS earthquakes, NSF awards and arXiv metadata. All three passed end-to-end worker pilots for January 4, 2016: 340, 18 and 344 records respectively (702 total). Every raw/parsed artifact and manifest was independently read back and checked; see `pilot-verification.json`. Other catalog additions are registrations pending source-specific access review and implementation. Legacy routing is now installed: 24 historical services dispatch to c7i and five mixed services run daily-only on t3. Separate frozen-seed runtime pointers isolate worker state; the old mutable global runtime is never shared across hosts. A bounded legacy ClinicalTrials pilot verified 100 records and a durable checkpoint; coverage remains partial. All 29 normal routes are gated pending source-specific validation. See [migration status](migration/MIGRATION_STATUS.md).

## Operations

Run commands from `/home/ec2-user/data-collection-processing` on the controller:

```bash
.venv-athena/bin/python -B -m constellation.control status
.venv-athena/bin/python -B -m constellation.control pause
```

`resume` enables eligible registered partitions immediately; do this only after worker IAM, connectivity and pilot checks pass. It does not resume legacy timers.

```bash
.venv-athena/bin/python -B -m constellation.control resume
```

Partitions include a source, dataset, geography, closed daily date interval, edition and extractor version. The initial adapters permit only audited fixed endpoints, empty extra parameters, dates on or after 2016, and closed historical UTC days. Arbitrary shell commands and endpoint URLs are not accepted from queue records.

A controller reconciliation timer is intentionally not activated during setup. Run `constellation.control reconcile` to classify an expired final attempt as blocked. Other expired leases are automatically reclaimable. Pausing prevents the next source request; in-flight requests can finish and preserve evidence. The 20-day operational deadline pauses work, but does not stop EC2 billing. Teardown follows coverage verification and an explicit handoff.

## Verification and remaining rollout

The historical CLI suite verifies 2016 defaults, explicit retry windows and unchanged daily origins. Adapter tests reject wrong date boundaries, provider error bodies, truncated pagination, duplicate IDs and corrupt S3 readbacks. Live RDS checks verify simultaneous claims, expired-lease recovery, stale-owner rejection and worker privilege boundaries. `check_rds.py` retains a clearly labeled synthetic blocked row and makes no provider requests.

Worker IAM, TLS database connectivity, two idle services and three bounded end-to-end pilots are verified. Collection is paused again, and legacy timers remain disabled. Next, clear the staged historical route gates, benchmark heterogeneous source workloads, implement the remaining new connectors, and audit their rights and feasible historical coverage. Normalization, semantic extraction and model training are later phases; the supplied documents contain unresolved calendar-versus-trading-day and horizon differences that do not affect today's collection rollout.

The selected regression run passed 59 tests. A broader preliminary run also found two existing PubMed fixture failures in `test_source_schedule_control.py` (`pubmed_primary_pmid_mismatch`); those unrelated parser fixtures have not been changed, and no full-suite pass is claimed.

## Verified current state

- Two raw workers and one legacy executor are enabled and idle; the RDS bulk flag is false and the pilot allowlist is empty.
- Three real partitions succeeded on the worker. One clearly labeled synthetic lease-test row is retained separately as diagnostics.
- The legacy Optima timers are disabled. The active/exited runtime-init unit only creates the RAM workspace; it performs no collection.
- The real market and news stream identities match their saved pre-change identities (`state-compatibility.json`).
- Remaining rollout includes activating validated historical routes, the other 91 new catalog integrations, rights/coverage audits, CloudWatch forwarding/alarms, and a representative capacity benchmark. A three-source one-day pilot does not establish the 20-day backfill capacity plan.

Example dry plan for an eligible implemented adapter (does not register or execute jobs):

```bash
.venv-athena/bin/python -B -m constellation.plan --source arxiv --end 2016-02-01
```

Adding `--register` saves partitions to the durable queue but leaves collection paused. Use `control resume` only for a reviewed plan. The internal daily request budgets are conservative operating caps, not claims about provider entitlements.

## API access inventory

The [API access checklist](API_ACCESS_CHECKLIST.md) covers all 158 entries: 19 new priority credential/account groups, nine commercial or conditional groups and five optional upgrades. Existing credentials, pauses, public routes and licence requirements are identified separately. The [CSV](source-access-requirements.csv) provides one row per catalog entry.

Current migration verification passed 58 collector/routing tests and 43 storage/runtime tests. See [migration status](migration/MIGRATION_STATUS.md) for deployed routing, remaining gates and live pilot evidence.
