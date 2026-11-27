# OpenAlex and KAKEN collection

The t3 controller runs daily collection. C7 runs the historical OpenAlex snapshot and the KAKEN fiscal-year backfill. The C7 jobs follow the existing worker batch schedule and pause before an EC2 stop. All four routes use the Constellation collection controls and resource slices. Each execution resumes from an S3 checkpoint. A cursor or offset advances after the batch passes readback. Coverage status reflects provider totals and unique record counts when API pagination ends.

| Source | Daily collection | Historical collection |
| --- | --- | --- |
| OpenAlex works | Closed UTC publication dates, with a one-day publication lag. The query includes OpenAlex’s core and expansion corpora. | The public 14 October 2026 works snapshot, filtered to publication dates from 1 January 2016 through the release date. A throttled API catch-up lane runs on t3 and covers the interval from that release through the daily origin. |
| KAKEN research projects | A current snapshot of projects whose award periods intersect Japan’s current fiscal year. | Projects grouped by their research start fiscal year, from FY2016 through the most recent closed Japanese fiscal year. The daily route covers the current fiscal year. |

The stored OpenAlex key supports publication-date queries. OpenAlex requires a Member+ or Partner plan for its update-date filters. Earlier works that receive later revisions may therefore differ from the public snapshot. OpenAlex collection covers works metadata. KAKEN retains the original project XML response and publishes project identifiers, titles, project types, and fiscal periods. The records link to the original evidence. [OpenAlex filters](https://help.openalex.org/api/filtering/) · [OpenAlex snapshots](https://help.openalex.org/access/snapshot/) · [NII KAKEN API](https://support.nii.ac.jp/en/kaken/api/api_outline)

## Status and evidence

- The source keys are `openalex_scholarly_graph` and `japan_kaken_funded_research`. Check `constellation-research-daily@SOURCE.timer` on t3 and `constellation-research-history@SOURCE.timer` on C7. Each matching service reports its exact window and counts in the journal.
- The S3 prefix is `research-data/constellation-backfill/research-feeds/v1/`. `checkpoints/` records API pagination. `progress/` tracks the publication date, fiscal year, or snapshot part to process next. `published/` contains the Athena manifests for committed batches.
- A committed batch is queryable before its window completes. API count changes or duplicate IDs leave the window partial. Resolve a partial historical KAKEN cohort before moving to the next year. Daily KAKEN reports the versions retrieved on that collection date.
- The pinned OpenAlex release has 1,898 compressed input parts. A changed manifest stops the import so the checkpoint cannot combine parts from different releases. The API catch-up and daily lanes have separate request allowances, totaling at most 9,400 requests per UTC day.
- The controller uses the corresponding fields in `newKeys`. The C7 worker uses `kaken-app-id` in `dataSourceAPIkeys`. The snapshot uses anonymous S3 access.

The metadata engine discovers committed daily and historical batches through the published manifests and queues them under contract `2.0.3`. OpenAlex output uses the `works_metadata` dataset and retains the complete work object. KAKEN output uses `grant_projects` and links each project to its matched original NII XML. Each mode shares the same metadata queue priority, so a sustained daily backlog cannot prevent the historical batches from being selected. Accepted jobs use the existing metadata publication service.

Athena tables are `optima_research_feeds.openalex_scholarly_graph` and `optima_research_feeds.japan_kaken_funded_research`. Select a collection mode to prune the other mode from the query.

On 21 November 2026 UTC, production Athena samples each returned 100 distinct records with evidence links. OpenAlex daily query `529be609-5d63-4551-8449-99d1e48c3c22` and historical API catch-up query `1a4da6bf-2e17-4316-bd94-f94c5063dd3d` verified publication from t3. KAKEN daily query `600fa608-3c31-4abd-9917-98748f88451f` and historical query `0780fe8f-a5e2-46b1-9ffa-5591706271ec` verified both hosts. The C7 OpenAlex snapshot canary retained 24 eligible works. The production snapshot and both backfills continue from their checkpoints.

```sql
SELECT source_record_id, window_id, raw_uri
FROM optima_research_feeds.japan_kaken_funded_research
WHERE collection_mode = 'historical' AND window_id = 'fy-2016'
LIMIT 10;
```
