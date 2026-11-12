# November 4 checkup repairs

Reviewed the supplied November 3 overview. Targeted repairs and live tests were performed November 4; this is not a full source-history audit.

## Completed

- `collection_health_exporter.py`: allow up to 32 MiB for the exact runtime-index object, keeping the ordinary 8 MiB metadata cap. Reads remain bounded and bodies are closed. The live 21,563,527-byte index loaded 51,713 paths. See [live checks](live-checks.json).
- Ran the normal health exporter with alert recording, without sending notifications. All 29 jobs inspected successfully; 19 service alerts remained. See [health refresh](health-refresh.log).
- `monitoring_overview.py`: separate actual services from historical scopes in overview counts and display the historical failure evidence timestamp. The 3,933-failure handoff is dated October 30, not a fresh November 3 count. See [handoff evidence](historical-autostop.json).
- `monitoring_runbooks.py`: historical-gap actions reference source receipts/checkpoints instead of fictitious systemd units. Updated only these two modules in the existing watchdog Lambda, retaining its original package backup and verifying successful deployment. See [deployment receipt](monitoring-deployment.json).
- 22 focused tests passed: `test_checkup1104`, `test_collection_health_repairs`, `test_monitoring_overview`, `test_constellation_launch`. See [test log](tests.log).

## Source probes and retry

- Census still rejects the stored key: `census_api_key_rejected`. Owner should confirm activation or update only `US-census` in `dataSourceAPIkeys`, then request a retest. No key values were printed.
- NSF February 29, 2016: three pages returned 53 unique records with exhausted pagination and no duplicates. See [probe](nsf-probe.json). This was a read-only source probe, not a publication run.
- Backed up the exact NSF job before allowing one additional attempt; original failure evidence remains. See [retry decision](nsf-requeue.json) and [latest queue status](nsf-retry-status.json). Latest status: pending, attempts 2. Committed capture and Athena recovery remain unverified.

## Remaining work

Publication queues, HKEX dependencies, patent duplicates, market gaps and unresolved historical scopes still require targeted replay and Athena verification. No blanket exclusion or global retry reset was applied. Existing owner pauses and historical migration remain in effect. SMS delivery is acknowledged and is not an owner task.

Copernicus's retained submission probe reports unaccepted dataset licences; this was not retested November 4. Owner should confirm acceptance for ERA5 single levels and ERA5-Land before engineering tests submission again.

The supplied November 3 audit's passing readbacks and receipt totals are dated evidence, not a fresh verification of every source. HTTP errors and empty results alone do not justify permanent historical exclusions.

See [today and tomorrow's owner actions](../../../data-source-status-2026-10-26.md).

## Updated Census key retest — 12:46 UTC

After owner confirmation, a fresh process loaded the current secret and repeated the February 2016 trade query. Census still rejected the key. A separate 2020 Census state-name query also returned HTTP 302 to `/data/invalid_key.html`. Key presence and formatting checks found no surrounding whitespace or URL value; no credential was printed. No collection recovery is claimed. See [retest receipt](census-updated-key-retest.json).

## Activation and terms acceptance verified — 12:51 UTC onward

Supersedes the earlier access failures above. Census returned 36 February 2016 trade rows after email activation. Both ERA5 datasets accepted tiny January 2016 requests, completed successfully and supplied validated downloads (25,171 and 25,116 bytes). These samples are local probe artifacts, not published production observations. See [API retest](activated-access-retest.json), [job status](copernicus-activation-job-status.json), and [download checksums](copernicus-download-verification.json).

Both sources remain enabled in daily configuration and the shared daily timer is scheduled. Historical queue inspection timed out; no historical retry state was changed and no resumed production capture or Athena publication is claimed. Structured NetCDF weather extraction remains outstanding. Owner activation/licence tasks are complete.
