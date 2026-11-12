# Chinese Clinical Trial Registry — reviewed and rechecked November 10, 2026

The earlier repair restored original HTML validation and the capture-to-Athena path. This recheck ran fresh queries with result reuse disabled, published six more accepted metadata batches, checked source/runtime state and removed the remaining discovery-only false incidents.

## Current verified result

| Check | Result | Athena query ID |
| --- | --- | --- |
| Original metadata aggregate | **94 observations, all raw-complete; 11 linked raw batches** | `1eb865e0-79b2-49cd-89a2-18dcf8e42fcc` |
| Metadata payload | Matching registration/project IDs, complete status, 73-field current detail | `8b40a008-6374-4e43-8c10-9f9c65deb31b` |
| Regulatory payload | Same current trial, 73 saved fields and populated `data_json` | `415b9fb0-304f-4136-8d63-baf1a41ea2fa` |

The most recent capture is **2026-11-10T18:51:43.795492Z**, registration `ChiCTR2600132684`, project `343036`. Its registration date remains September 17; November 10 is the new observation time. The 94 observations include repeats and older captures; they are not a count of new/unique trials or complete history.

The source is enabled under contract **2.0.3**, with zero consecutive raw failures. Six additional accepted batches were published in this recheck (`publication.json`: five plus one). Current metadata and regulatory records have substantive trial fields and original HTML evidence, rather than just article/trial URLs.

## Remaining false failures corrected

The only three remaining failed ChiCTR metadata jobs referenced **website-discovery pages**, not original trial records. Their raw receipts explicitly identify that artifact type. They are now classified as non-trial inputs, retaining all files and job/audit history. The one open `public_capture_is_discovery_page_only` incident tied to those jobs was resolved.

The controller now applies this classification to later confirmed discovery-only ChiCTR receipts. It does not discard actual trial inputs, weaken project/registration/date/full-field validation, or claim that discovery pages are complete trials. Failed trial material still remains an actionable validation error.

**55 focused tests passed** for ChiCTR identity/HTML validation, incomplete-render retries, date formats, collection pagination/resume, regulatory publication and discovery-only classification.

## Capture and processing schedules

- `optima-chictr-daily.timer` is enabled on the controller. Next scheduled run at verification: **November 11, 08:36:57 UTC / 09:36:57 Europe/Madrid**.
- Its last invocation finished with systemd `Result=success`. Collector exit 2 represented the configured **partial/page-limit** result. It saved partial September catch-up windows; those windows remain unfinished. A bounded invocation finishing is not full registry completion.
- Existing daily limits remain one window, two pages and a 1,000-record budget. Saved cursors support continuation; source-change detection and gateway backoff remain in force.
- Metadata worker/controller and publication schedules remain active. The worker was accepting other sources during inspection; all 15 collection workers were active.
- Historical public discovery is scheduled, but discovery receipts alone do not establish historical structured-trial coverage. Older-window reconciliation, full registry history, historical vintages, attachments and verified Constellation entity matching remain separate from this pipeline review.

No owner-paused sources were resumed. No new ChiCTR login, key or scraping subscription is required based on today's successful capture and readback.

## Your Athena check

Use **us-east-1**, **AwsDataCatalog**, workgroup **optima-collected-data**, and turn **Reuse query results off**. The source key is **`chictr`**.

```sql
SELECT source_key,
       count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations"
WHERE source_key = 'chictr'
GROUP BY source_key;
```

Twenty random metadata rows:

```sql
SELECT *
FROM "AwsDataCatalog"."optima_metadata_engine"."source_observations"
WHERE source_key = 'chictr'
ORDER BY rand()
LIMIT 20;
```

Twenty random regulatory rows:

```sql
SELECT *
FROM "AwsDataCatalog"."optima_regulatory_pilot"."research_records_windows"
WHERE source = 'chictr'
ORDER BY rand()
LIMIT 20;
```

In metadata, inspect `labelled_json` → `payload.data.fields`; in the regulatory table inspect `data_json` → `fields`. To inspect the most recent verified sample specifically, add a filter for `ChiCTR2600132684` using `source_record_id` in metadata or `provider_id` in the regulatory table.

If a query still returns no rows in your console, compare the region/catalog/workgroup and exact table/filter above with these successful query IDs. No new evidence suggests a current zero-row dataset. We have not observed your console settings, so an earlier/cached or different-context result remains a possibility rather than a confirmed diagnosis.

Evidence: `athena-verification.json`, `metadata_sample.json`, `curated_payload.json`, `publication.json`, `remaining-jobs.json`, `discovery-receipt-classification.json`, `open-incidents.json` (before resolution), `classified-incidents-before.json`, deployment/worker results and `tests.log`. The [earlier repair report](../2026-11-10-chictr/README.md) retains live scraper and original raw-validation evidence.
