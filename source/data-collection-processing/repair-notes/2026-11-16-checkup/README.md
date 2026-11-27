# November 16 collection repairs

This review uses the attached alert email, current service logs, provider responses, exact collection checkpoints and publication receipts. A running service alone is not a completed pipeline. Original failures, raw objects and incomplete scopes remain retained.

## Verified repairs

- **USGS cobalt, 2019:** replaced the obsolete guessed URL with the PDF linked by the [official USGS media page](https://www.usgs.gov/media/files/cobalt-mcs-2019-data-sheet). Replayed the exact report and verified its publication in Athena. One report observation; this is not a claim of complete mineral coverage. Athena verification query: `33d372bb-e661-4bcd-a427-6ca244d2d6a5`.
- **IMF PortWatch, January 23, 2019:** the previously failing request now succeeds. Committed and verified **2,065 observations** in Athena. Query: `6b686bb2-4278-462a-b246-cbf784029f21`. Other historical days remain separate scopes.
- **Census:** all **eight** formerly failing older commodity/month queries were replayed. Each returned HTTP 204 while its same-month total query returned data. They are evidenced empty query results, **not zero trade values**. Ten October 2026 queries remain incomplete because that period is not yet available; they retain retries and become actionable again if they outlive the expected lag. All eight empty-window coverage partitions have now been published and verified in Athena; the record count is zero, not a measured trade value of zero.
- **Finlight:** reran the failed capture; the latest pass committed five completed scopes containing **650 observation occurrences**, with a subsequent scope continuing at its page allowance. The refreshed health report no longer lists the earlier news error. This does not prove that the incomplete November 13 news window has been published.
- **Copernicus:** credentials work; the provider's sampled 100 recent jobs all reported success. Two exact legacy December 2023 scopes were replayed and committed their NetCDF artifacts. Both scopes are now published and verified in Athena. Structured weather extraction remains distinct: temperature/precipitation columns are not yet certified.
- **HKEX:** isolated the September 30 window failure to news ID **12352175**, a provider-labelled 90 MB offering circular. Added a 128 MiB limit restricted to official HKEX PDF paths. The two bounded replays exhausted the **1,367-row English index**, committing **1,411 observations** including separately identified Chinese originals. Dependent disclosure-document capture also completed with **six selected documents**. Their publication and downstream candidate manifests still need verification; capture is not treated as a finished Athena pipeline.
- **Publication scheduling:** replaced the unbounded inventory bridge with a rotating 128-entry pass and a conditional saved cursor. Existing queues and conflict receipts remain retained. Restarted only the old bridge scan after acquiring its preparation lock, which prevented Glue publication from starting during the stop. The regular publisher was restarted; other collection jobs continued.

## Evidenced exceptions, not fabricated complete data

- **ALFRED DTWEXBGS:** the provider's vintage catalogue begins **February 4, 2019**. Eleven exact requests pinned to a realtime interval ending in 2018 are now `accepted_unavailable`. Other series and later vintages remain eligible. Evidence: `provider-probes.json`.
- **medRxiv before launch:** **41** saved failed scopes were changed to the existing reviewed `source_not_operating` exception. Post-launch full-text failures remain visible.
- **WTO TP_B_0380 / TP_B_0180:** the provider explicitly rejects a year filter because these indicators have no time dimension. Both exact old 2016 requests now have an evidenced exception. Both periodless probes returned **141 rows**; the current snapshot routes remain enabled. Those snapshots are not 2016 measurements.
- **EDINET:** [official API specification, section 3-1-3-3](https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/download/ESE140206.pdf) documents deletion of listings older than ten years. The old-day probe returned body status 404 while a current-day probe returned 2,118 entries with the same key. The collector now accepts only an actual 404 for an exact historical day safely outside that retention boundary, with saved provider evidence. It does not exempt recent 404s, authentication failures, or scopes with committed records. The separately logged pass completed all **300 applicable old failed days**, with a provider response and exception receipt for each; see `second-results.json`.

The gap audit now consults a newer matching specialist checkpoint before repeating an immutable old failure. A complete replacement must have a matching complete, exhausted manifest. EDINET exceptions additionally require a checksummed provider 404 and the reviewed retention rule. Expected recent Census publication lag stays incomplete but is deferred from actionable historical-gap reporting.

## Work still open — implementation

| Priority | Remaining work | Completion evidence required |
| --- | --- | --- |
| 1 | Finish publication and candidate verification for the recovered HKEX/disclosure window | HKEX and six selected document captures are complete; verify candidate manifests, publication receipts and Athena payloads |
| 1 | Replay FDA, EMA/CTIS and ClinicalTrials historical windows from the email | Resolve old pagination/count/source-change generations, verify exact scopes, then publish; current successful captures do not cancel different historical gaps |
| 1 | Investigate post-launch medRxiv PDF access | Live replay still returned HTTP 403. The duplicate-row fix passes tests. Decodo returned HTTP 200 and PDF-shaped content, but that probe failed strict PDF validation; naive UTF-8/Latin-1 reconstruction is unsafe. A binary-safe gateway response mode must be verified before production fallback |
| 2 | Finish Zenodo/DataCite pagination recovery | Bound changing scopes as needed and verify full counts; do not loop indefinitely on a mutable total |
| 2 | Continue Copernicus downloads and implement/verify structured NetCDF extraction | Raw-file capture alone is insufficient for specialist weather features |
| 2 | Reconcile remaining TED and USAspending scopes | TED's old permission errors have newer successful scopes, but its one saved count mismatch remains; USAspending replay committed more pages and continues at `page_budget` |
| 2 | Review missing MHRA historical designation dates | Retain current undated rows; a current register cannot establish an unavailable historical event date |
| 2 | Resolve market identities and empty-price evidence | Current snapshot: **174 daily / 201 historical symbols**, **56 reviewed exclusions**. Do not extend exclusions without issuer/listing evidence |

Product search runs but remains `product_directory_required`: Constellation has no named product entities to search yet. This is an engineering dependency, not a request for the owner to type every product name.

## Owner actions

**The completed repairs need no new access. The remaining binary-safe PDF route requires a separate Web Data API Bearer secret, as listed below. SMS is working and is not an action item.**

1. Run the two bounded SQL checks below to inspect the recovered payloads. If a needed specialist field is absent, report the source and field; SQL visibility is not certification of all transformations.
**Owner decision, November 16:** EDINET historical year **2016 is not required**. It is excluded from collection retries and actionable alerts. No alternative archive acquisition is needed. Previously captured evidence is retained, and other EDINET years/current daily collection remain in scope.

2. **Decodo support task closed:** the owner confirmed that base64 output is not offered. The tested PDF route remains disabled. No further base64 support request, replacement Web Data API key or new purchase is requested. Alternative original-download/proxy transport is engineering work; see [current findings](../2026-11-16-decodo-web-data/README.md).
Other collector defects remain implementation work above; no manual account change has been established for them.

```sql
-- Recovered 2019 cobalt report: one observation with nested report payload.
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE window_id = '74fe11b37ff527601b5b65f90b14b47ab93b98fefc591ba95d03f38ca4340367'
ORDER BY rand()
LIMIT 20;
```

```sql
-- Recovered January 23, 2019 PortWatch scope: random examples from 2,065 observations.
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE window_id = '04760d5645a401d57e4b70a1b7e503d5b255fb880d73322ed3c70029d38d84ef'
ORDER BY rand()
LIMIT 20;
```

## Logs and verification

- `focused-tests.log`: **128 tests passed**, covering collector, gap, publication and disclosure changes.
- `deployment-result.json`, `*-deployment-result.json`: immutable deployment keys/checksums and runtime results; original runtime files were backed up on the worker.
- `replay-results.json`: first 74 exact scopes; 52 accepted exceptions, six complete, eleven continuing/deferred and five failed at that pass. Four Census transport failures subsequently recovered; see `second-initial-results.json`.
- `publication-results.json`: initial verified USGS and PortWatch receipts. `all-publication-results.json`: all **12 recovered windows verified in Athena** (eight empty Census coverage partitions, two Copernicus artifact observations, USGS and PortWatch).
- `second-initial-results.json`: the subsequent four Census recoveries, two WTO exceptions, two Copernicus captures and remaining medRxiv 403.
- Worker durable logs: `/opt/constellation/tmp/checkup1116/{replay,second,publish,all-publish}.log`.
- S3 per-step evidence: `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/repairs/2026-11-16/`.
- Reviewed exceptions are also saved under `research-data/operations/specialists/reviewed-gaps/`. They are availability decisions, not observation rows or claims of complete history.
- Latest service check found no failed worker units. Five ordinary historical workers were active; metadata processing timers and the independent streaming timer were enabled and operating between bounded passes. This does not clear source validation holds.
- Reddit, Bluesky, GitHub source capture, Marketaux and NICE remain intentionally paused. No SMS test or email was sent manually.

```sql
-- Raw Copernicus artifact observations; structured weather extraction remains pending.
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE window_id IN ('a6fd63a59fd548b98bdd28fe10b17ab993cf5bdf946f6370da6a3240128a2c19', '9c533cad1f6e02712e74689121f97b816e6c20295597c2dee869f76891ea8a22')
LIMIT 20;
```

```sql
-- All eight evidenced empty Census windows should have records = 0.
SELECT *
FROM optima_specialist_inputs.source_coverage_windows
WHERE window_id IN ('a47f2c40ad09e4a0ea3e8c676d38671040c494266b306498c0ea98a0081a21c0', 'd95c544ed0f78caf674558112f8a8b4e04b022d9b5a071c1d7a1719fcd76b657', 'f209c13c648d827fc23092e74935b871c6c3a21836f44756c974ec970185027c', 'ffe0a296ced78e89ce8a2e8a5cc380748d7f6aee4872e71d49bcec3702cc8ab3', '0ab875e973f5ec7914643387d264c3b06e1aaa75fee4f7521bd09532cfd1df47', '32185d0f4d9458bc313641fe13e0883d14f877f845ec49e33f83463865179516', '448127bd2a20711245767738a69294df8ca0cc2b2f7da3f0278c6d1ef89c9a66', '7ef9e5c9e1056b8dbed5446dada1ebd54cef0faf24ebbef3cfc81624c421d20b')
ORDER BY window_start;
```
