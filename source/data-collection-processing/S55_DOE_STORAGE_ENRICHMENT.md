# S55 — DOE storage documents, technical evidence and funding/project facts

Implemented on 2026-10-18. The original source `doe_storage_program` now parses the landing page and discovers document links. `doe_storage_pipeline.py` runs after complete daily capture, retrieves original evidence and publishes three separate sources in dataset `specialist_inputs`:

| Source | Contents |
| --- | --- |
| `doe_storage_documents` | Document identity/version, title, explicitly published date where available, type, extraction status/limits, discovered links, counts, original-file evidence and full extraction reference. |
| `doe_storage_benchmarks` | Source-attributed technical statements, numeric tokens, metric candidates, target/model/template classifications and extracted table previews/references. Values are not automatically certified product measurements or converted into comparable units. |
| `doe_storage_funding` | Funding/project statements, opportunity/project IDs, amount mentions, stage mentions and source table rows that preserve recipient/amount columns together. Opportunities, selection announcements and awards are not assumed to be executed grants or disbursements. |

The released parser version is `doe-storage-evidence-v2`; filter by `payload.extraction_version` to exclude early launch validation outputs. The current backfill job is `doe-storage-backfill-2026-10-18-v2`.

## Discovery and evidence

The backfill pins the ten existing landing-page observations in `reports/doe-storage-backfill-2026-10-18/input-batches.json`, validates their checksums and parses every distinct saved HTML version for links. It then follows current DOE program pages, technology assessments, ROVI documents, Storage Innovations/Liftoff, the long-duration demonstrations program and PNNL's cost/performance report hub. The original broken cost-database URL is retained as an unavailable-document gap, rather than replaced silently.

DOE CMS links are normalized to their public `www.energy.gov` mirror, keeping percent-encoded filename characters such as `%23`. Relevant links are followed only on the exact allowlisted public DOE, DOE funding-exchange, NETL, PNNL, Sandia and OSTI hosts. Off-scope links and limits are recorded. This does not crawl all DOE websites or obtain restricted/account-only data.

Successful original responses are preserved by SHA256 in `source_documents/doe_storage_documents/{sha256}`. Full parsed text, PDF pages/tables, HTML blocks/tables, spreadsheet cells, discovered links and extracted facts are saved as immutable JSON in `source_documents/doe_storage_extractions/{sha256}`. Each output points to the original evidence and this extraction reference. The raw file is always the complete source evidence when indexed extraction limits apply.

Current bounds in `config/doe-storage.json`: depth four; 300 documents per job; six documents per invocation; 32 MiB accepted document size; 250 PDF pages; 30,000 spreadsheet cells; 400 indexed statements per category. Overflow, OCR needs, unsupported archives, failed downloads and scope exclusions remain visible. PDF tables retain page/bounding box/context; Excel preserves sheet/cell coordinates, values, number formats and original formulas without evaluating them. Source units, conditions, footnotes and methodology still require review before comparisons. The parser does not claim OCR or chart digitization.

## Identity and matching

The worker reads a consistent, read-only RDS company/product directory snapshot once per job and archives its hash. Exact names and reviewed company aliases generate mention candidates with source text. They do not establish award recipient, partner, manufacturer, tested product or commercial relationship. Technology categories provide sector context and never bind every product using that technology.

RDS company and product tables were empty at launch, so current outputs may be `unmatched_directory_empty`. Original parties and project information remain in source statements and table rows for subsequent resolution. Production company/product relationship review and event emission are separate processes.

Document source identities combine canonical URL and semantic content hash. Multiple URLs can still expose the same original report: downstream comparison/event logic must deduplicate using original SHA256, semantic version and report/project identity, not ingestion count. Repeated daily observations are not new developments.

## Backfill, daily operation and completion email

`optima-doe-storage-backfill.timer` resumes the pinned document backfill and checks completion. `optima-doe-storage-daily.timer` processes documents after an exhausted, complete same-day S55 landing capture, using Europe/Madrid for the daily gate. Both probe approximately every five minutes, share a capture lock, retain checkpoints and retry failures up to three attempts with a 15-minute delay. The daily worker resumes unfinished prior daily jobs before starting another.

State: `doe-storage.sqlite3`; local status receipts: `reports/doe-storage-backfill-latest.json` and `reports/doe-storage-daily-latest.json`; S3 state: `operations/doe-storage/jobs/{job_id}/`. Pinned backfill inventory/configuration and the completion receipt are archived there. Original archived bytes are reused on retry so a mutable URL cannot silently change a partially committed version. Parsed extractions can be reused for identical URL/bytes/parser versions.

The email to `randall@optima-holdings.com` uses the existing confirmed SNS email topic. It waits for all queued URLs to reach a captured or explicit-gap outcome, every emitted batch to be verified by the committed Athena index, and exact row/distinct-record counts for all three output sources and this job/version. A successful capture log or queued publication is insufficient. The email includes output counts, quality/scope/failure totals, sample gaps and the full completion receipt location. Completion is scoped to this bounded inventory; it does not certify exhaustive historical DOE coverage.

The original source retains `historical: false`: manufacturing historical landing-page snapshots would add no missing reports. This backfill recovers accessible historical documents through their original links and current official report hubs. Publication dates, report reference years and current retrieval dates stay separate. `point_in_time_eligible` remains false; current retrieval does not establish historical public availability.

## Inspect the enriched evidence

```sql
SELECT source, count(*) AS observations, count(DISTINCT record_id) AS document_versions
FROM optima_collected_data.observations
WHERE source IN ('doe_storage_documents','doe_storage_benchmarks','doe_storage_funding')
  AND dataset = 'specialist_inputs'
  AND json_extract_scalar(payload_json,'$.extraction_version') = 'doe-storage-evidence-v2'
  AND json_extract_scalar(payload_json,'$.job_id') = 'doe-storage-backfill-2026-10-18-v2'
GROUP BY source;
```

For examples, filter one of these sources and select `payload_json`; the technical/funding statements are under `$.data.facts` and original extracted tables are available through `$.extraction_reference`. See the S55 section in `ENTITY_DISCOVERY_ROLLOUT_PLAN.md#sql-checks` and the S55 integration directions in [event integration](ENTITY_DISCOVERY_ROLLOUT_PLAN.md#event-pipeline).
