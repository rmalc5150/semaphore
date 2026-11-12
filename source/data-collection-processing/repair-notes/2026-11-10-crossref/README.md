# Crossref proceedings — reviewed November 10, 2026 (DOI metadata scope)

The configured collector captures DOI-registered **proceedings-article metadata**, but metadata processing stopped after four `missing_verified_raw_artifacts:full_text` failures. The gate incorrectly demanded publisher papers. Crossref documents that its API supplies deposited metadata and links to publisher content, rather than the full texts themselves. [Official API description](https://www.crossref.org/documentation/retrieve-metadata/rest-api/), [full-text access explanation](https://www.crossref.org/documentation/retrieve-metadata/rest-api/text-and-data-mining-for-researchers/).

Contract 2.0.3 validates the whole returned provider record against the original checksummed API response, DOI, work type, source URL and every returned field. Projected, modified, mismatched or index-only records cannot pass. Missing deposited abstracts are explicitly flagged; metadata is not labelled as a full paper. Titles, authors, publication dates, meeting/event dates, licences, abstracts and publisher/full-text links remain available exactly where the provider supplies them. Their presence does not establish access to the linked paper or a historical metadata vintage.

## Verified Athena results

| Check | Verified result | Query ID |
| --- | --- | --- |
| Original metadata aggregate | **321 observations, all raw-complete; 11 linked raw batches** | `62e7f35d-3c00-4309-8a82-9ee83c850343` |
| Fresh metadata payload | DOI/title/type/publisher and complete saved metadata | `51a53236-a504-4c58-be82-713062394a20` |
| Fresh conference curated payload | Same DOI/title/publisher and publication date, full `data_json` | `e6d2e524-95c6-4df2-a926-8aef7e7e80af` |

The nonempty live probe retrieved DOI `10.51161/v-convesp/78963` at **2026-11-10T20:43:51.464713Z**. It is one explicitly selected current DOI record, not a complete daily window. Its source publication date remains **2026-05-18**; the meeting dates remain separate provider fields. Publication receipt verification query: `66a90e76-8beb-4972-af31-174bd4dd1472`.

Counts are observations and include repeated DOI retrievals. They do not mean 321 unique papers, complete proceedings coverage or complete historical publication. Source state is enabled, zero consecutive raw failures.

## Repairs and continuing work

- Requeued **297 unfinished metadata jobs** under the corrected contract. All four original failed batches passed validation and replayed (**128 observations**). Verified accepted batches were published, including the new live probe.
- Original API pages saved by the alternate public-capture route now expand into real DOI records before labelling. The response hash is not treated as a publication ID; complete original data and checksum provenance remain attached.
- The original controller collection/publication jobs were waiting for the shared supervisor lock. Their replacements run independently: capture on worker `i-06241bd1c4e91c2fc`, publication on the controller. Old jobs had no child collectors/publishers running when stopped. Old timers were disabled after replacement verification; their migration and the replacement publisher are recorded in `config/collection-monitoring.json`.
- Original universe snapshot and operational checkpoints were preserved. The old daily cursor is **2026-11-10**, meaning completed update-date windows through November 9. The old **2021-origin** archive cursor reached 2023; that checkpoint is retained and is not mistaken for coverage back to 2016. The configured **2016-origin** route has its own checkpoint.
- Fixed bounded continuation for recent Crossref cursors. The large 2016-origin first window advanced **12,000 → 24,000 → 36,000 → 48,000 records**, with inherited page chains and `resumed_from_run_id` evidence. It is still partial against a provider count of 83,570 at the observed snapshot; these raw counts are not all published. Old/invalid cursors restart safely; duplicate and total-count checks remain enforced.
- A separate January 3, 2016 query completed with **zero returned records** and saved its coverage evidence. It is an empty provider result for that query, not a fabricated data record or archive completion claim. The nonempty fresh DOI probe supplies the end-to-end payload proof above.
- **43 focused tests passed**, covering exact metadata equality, raw checksums, projected responses, archived API-page expansion, DOI/type identity, cursor continuation/expiry, native curation, checkpoint preservation, publication bridging and isolation of daily failures from historical attempts.

## Schedules and bounds

| Timer | Host | Work |
| --- | --- | --- |
| `optima-crossref-resumed.timer` | Worker | One daily update-date continuation and one historical publication-date continuation per invocation. |
| `optima-crossref-publication-resumed.timer` | Controller | Bridge committed complete windows and publish at most one pending window with verified Athena receipt. |

Both continue **two minutes after completion**. Each service has a **384 MiB / 20% CPU** limit and a five-minute service bound. Capture limits each mode to 24 pages and a 110-second deadline; a failed daily attempt cannot stop the historical attempt. Each outcome is saved under `constellation-backfill/conferences-resumed/receipts/`. Original capture task identities and saved raw material remain intact.

Recent partial cursors are eligible for continuation for three minutes; actual provider expiry is still handled as a failure/restart. Older/unusable cursors start a new immutable attempt. Checkpoints, count reconciliation and original evidence determine completion—not a timer firing or a successful process exit. A very large window remains unfinished until its provider pagination exhausts.

The native source covers registered proceedings articles globally. Unregistered presentations, many journal-supplement abstracts, missing abstracts, full publisher papers, verified company/product matching and point-in-time availability remain outside this review. Historical capture and metadata/publication backlog continue. No owner-paused sources were resumed, and no new paid API or account was required.

## Your Athena check

Use **us-east-1**, **AwsDataCatalog**, workgroup **optima-collected-data**, and turn result reuse off.

```sql
SELECT source_key,
       count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM optima_metadata_engine.source_observations
WHERE source_key = 'crossref_proceedings'
GROUP BY source_key;
```

Twenty random metadata observations, with the complete provider record inside `labelled_json` → `payload.data`:

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'crossref_proceedings'
ORDER BY rand()
LIMIT 20;
```

The fresh curated probe is one record. This partition filter keeps the check small and avoids scanning the full conference archive:

```sql
SELECT *
FROM optima_conference_research.conference_observations_windows
WHERE window_id = '1390dba3cde6617acc1bc5fd8f13b730b67e015f342a3b396c65bc5136d2ddfe'
ORDER BY rand()
LIMIT 20;
```

Inspect `data_json` for the complete returned fields and `record_json` for source evidence/provenance. A record without a deposited abstract legitimately lacks that field; it is not a scraper failure. The review checkbox certifies this verified metadata route, not availability of full proceedings papers.

Evidence files: `failed-batch-validation.json`, `migration.json`, `progress-before.json`, `capture-status.json`, deployment/replay results, `fresh-capture.json`, `fresh-verification-receipt.json`, `athena-verification.json`, `metadata_sample.json`, `curated_payload.json`, `final-status.json`, worker results and `tests.log`.
