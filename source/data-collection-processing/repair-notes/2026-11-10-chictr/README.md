# Chinese Clinical Trial Registry — reviewed November 10, 2026

> **Later recheck, November 10:** the metadata query now returns **94 raw-complete observations / 11 batches**. Six additional accepted batches were published; discovery-only false incidents were classified and resolved. See the [current recheck and SQL](../2026-11-10-chictr-recheck/README.md). The counts below preserve the original repair evidence.

The empty metadata SQL result was caused by stopped metadata validation, rather than missing source material. Four jobs had failed with `missing_verified_raw_artifacts:provider_record`: the generic validator rejects HTML without a source-specific document check.

## Repairs and live verification

- Added an original **rendered trial-detail HTML** validator. It verifies the official HTTPS detail URL/project ID, registration number, registration date and the entire parsed field list. Search pages, unrelated trials, changed/partial field lists and access-block pages cannot substitute for the original detail.
- Shared the existing table parser between capture and metadata validation. Both provider date-only and date/time formats are compared at their declared day precision; original strings remain unchanged.
- The metadata worker now reads only evidence for the matching trial/project. It can find the valid original among multiple archived responses for that URL; it does not accept an earlier incomplete rendering merely because a table exists.
- Added a capture-side readiness check: an incomplete scaffold table is retained as evidence and retried before a trial detail is accepted. Existing gateway-429 backoff and durable cursors remain in force.
- Registered contract **2.0.3** and requeued **23 unfinished jobs**. All four original failed batches passed original-page validation and replayed successfully: **38 legacy observations**.
- Live bounded scraper request succeeded at **19:51 Europe/Madrid** on November 10. Saved a new full original HTML and **73-field** current-detail record for registration `ChiCTR2600132684`, project `343036`, then published it through both metadata and regulatory Athena paths. Other sampled legacy records have 73–75 fields.
- **45 focused tests passed**, covering identity/origin, complete field equality, date formats, incomplete-render retry, collector pagination/resume and regulatory publication.

Metadata result: **39 raw-complete observations / five linked raw batches**, including the fresh November 10 capture. These are observations, including a refreshed existing trial; they are not 39 newly registered or unique trials.

Query evidence:

| Check | Athena query ID |
| --- | --- |
| User's metadata aggregate — now returns data | `c2a1ed67-0b13-47cc-9c48-66581c4b680c` |
| Metadata payload — IDs, complete status and field counts | `67191703-599d-4066-bcd1-64dd3a1eab18` |
| Regulatory payload — fresh record, 73 fields and full `data_json` | `9804996b-7bb4-42f5-a769-c0e30d0ba27d` |
| Fresh regulatory publication receipt/count verification | `93a4b74d-b6eb-4fa4-8485-09295e181d58` |

Files: `athena-verification.json`, `metadata_sample.json`, `curated_payload.json`, `fresh-capture.json`, `fresh-publication.json`, `failed-batch-validation.json`, `final-status.json`, `tests.log`.

## Collection and engine status

The source is **enabled**, contract 2.0.3, **zero consecutive raw failures**. Reviewed-source date queues isolate a later failed scope instead of stopping the source. Original failed attempts/raw objects remain available for audit.

The dedicated **controller** timer `optima-chictr-daily.timer` is enabled. At verification its next run was **November 11 around 09:37 Europe/Madrid**, including jitter. Its existing bounded invocation uses one window, two pages and a 1,000-record budget; partial/page-budget exits are continuation status and do not establish completion of the registry. Corrected the stale config text claiming ChiCTR had no dedicated schedule.

Both daily and historical collection controls are enabled. The historical public-capture route is scheduled, with recent successful executions and another pending. **Those public discovery receipts do not prove full structured trial-history coverage.** The actual trial collector's exhaustive year-page traversal, saved cursors and source-change checks remain in place. Older registration-window reconciliation and registry-wide completeness remain separate coverage work. The new one-registration live repair proves today's end-to-end path, not a full new registry harvest.

All **15 collection workers** were active; the metadata worker's last completed run succeeded. The controller metadata timer was enabled and its last completed result succeeded. Other sources' pre-existing validation holds remain separate. No owner-paused sources were resumed.

An old worker picked up four jobs before deployment completed; those exact jobs were reset only after confirming the code deployment, then all passed under the new worker. The superseded replay's failed flag was cleared after successful replay and Athena proof; reports and logs remain in `premature-replay-jobs.json` and `replay-command-result.json`. Final worker results: `worker-check-command-result.json`, `final-worker-command-result.json`. The fresh single-detail repair is a bounded one-off; it adds no duplicate permanent collection timer.

## Your action

**No new ChiCTR login, key or scraper subscription is required based on the successful live request.** Optional: run the SQL below and inspect representative payloads. This review covers the original public-detail material and the working capture-to-Athena path; it does not certify full registry history, historical registry vintages, protocol attachments or verified Constellation entity matching.

Use **us-east-1 → AwsDataCatalog → optima-collected-data**, with result reuse disabled:

```sql
SELECT source_key, count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations"
WHERE source_key = 'chictr'
GROUP BY source_key;
```

Twenty random metadata observations, with complete JSON in `labelled_json` at `$.payload.data.fields`:

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'chictr'
ORDER BY rand()
LIMIT 20;
```

Twenty random regulatory records, with original field lists in `data_json` at `$.fields`:

```sql
SELECT *
FROM optima_regulatory_pilot.research_records_windows
WHERE source = 'chictr'
ORDER BY rand()
LIMIT 20;
```

To inspect today's exact refreshed trial, use `WHERE source = 'chictr' AND provider_id = 'ChiCTR2600132684'` and order by `last_observed_at DESC`. Its registration date remains September 17; November 10 is the new observation time, not a fabricated registration date.
