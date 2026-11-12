# S57 — CAISO archive provenance, intervals, revisions and storage context

Implemented on 2026-10-18 in `caiso_enrichment.py`, `caiso_pipeline.py` and `caiso_transport.py`, version `caiso-market-evidence-v1`.

## Outputs

The original `caiso_prices / specialist_inputs` source continues to preserve component rows. Its daily adapter now adds member provenance, archive inventory references, normalized timing and numeric prices, and records the full interval start in top-level `event_at` with second precision. Previously saved observations retain their original timestamps; enriched interval observations provide precise times for the backfill.

The dedicated worker produces these sources in `specialist_inputs`:

| Source | Meaning |
| --- | --- |
| `caiso_archive_inventory` | Original ZIP SHA/bytes, member names/SHA/CRC/bytes/columns, total and selected row counts, query/report version, transport and original response evidence. |
| `caiso_price_intervals` | Joined total LMP, energy, congestion, loss and GHG prices by node, market and UTC interval, with component reconciliation, source row locations, revision IDs and original definition-document evidence. |
| `caiso_ancillary_prices` | Ancillary prices by market, region, service and interval, with original value field and published units. These are not energy prices or revenue. |
| `caiso_storage_indicators` | Pacific operating-day negative-total-price hours, configurable spike counts, congestion episodes, duration-weighted volatility and chronological single-interval spreads. Complete and partial-day summaries are distinguished. |
| `caiso_project_exposure` | Price context for explicitly documented project-node mappings and reviewed, dated owner/operator/installed-product relationships resolved against active RDS entities. Hubs are excluded. |

No production company/product event is created. Event-pipeline integration is described in [event integration](ENTITY_DISCOVERY_ROLLOUT_PLAN.md#event-pipeline).

## Original evidence and schema

ZIP bytes are preserved at `source_documents/caiso_prices/{sha256}`. Each selected row records the archive/member checksum, member filename and logical CSV row number, query parameters, report version and original value-field name. The standalone original-row collector saves an additional inventory object under `source_documents/caiso_archive_inventory/`. Members remain recoverable losslessly from the original ZIP; storing a second XML representation is not required for CSV responses.

Archived CSV parsing streams decompression and computes member checksums while selecting requested nodes, rather than retaining all-node CSV contents in memory. Unsupported members, provider error XML, duplicate filenames and expansion/size violations are failures, not successful empty windows. Provider XML errors remain in the archived original response; API retries fetch a fresh response until a valid archive can be frozen. Once a validated archive is partially committed, retries reuse those exact bytes.

The misleading source value column can be `MW`, `VALUE` or `PRC`. Energy price outputs explicitly use USD/MWh. Ancillary clearing prices preserve the published USD/MW label without inventing a settlement-period conversion or multiplying it into energy revenue. Regulation, spinning and nonspinning service types/regions remain distinct source fields.

The official CAISO market manual is archived with its checksum and linked to interval definitions. The current five-field profile checks `LMP = MCE + MCC + MCL + MGHG` with a USD/MWh 0.001 rounding tolerance. CAISO’s archived Fall 2017 interface specification (PDF pages 18 and 72) documents four DAM fields: total LMP plus energy, congestion and loss. A separate legacy profile applies only to the three known CAISO hubs, DAM, dates before 2026-05-01, and archives containing exactly those four fields. It validates `LMP = MCE + MCC + MCL`, preserves GHG as null rather than inventing zero, and records the profile ID and original definition evidence. Unknown/missing components outside that documented profile remain review gaps. Initial legacy observations flagged under the strict profile are retained and explicitly reanalyzed; this is a definition review, not a price correction. Missing or duplicated components, nonnumeric values and mismatched operating dates are flagged. Missing GHG is never assumed to be zero; unrecognized older schema/applicability questions remain review gaps. A negative congestion component is not a negative total LMP.

## Timing and revisions

Preserve UTC interval start/end, Pacific start/end including offset and repeated-hour `fold`, reported operating date/hour/interval, calculated operating date, and duration. Query current reports on complete Pacific operating days: spring/fall transition days contain 23/25 hours. Saved UTC-day archives can span two partial Pacific days. Summaries are rebuilt from latest observed interval versions so neighboring archives can complete the day, while earlier partial summaries remain auditable.

Interval identities exclude prices and packaging; price revision IDs use the interval and component values. ZIP changes alone do not constitute a price correction. Original ZIP identity, retrieval time and source metadata remain separate. Previous observed revisions are retained; older saved evidence does not overwrite a newer observed version. This is observation history, not proof of when CAISO originally published or corrected a historical price. `point_in_time_eligible` remains false.

## Market and historical scope

The expanded worker requests:

- `PRC_LMP`, version 12, DAM hourly prices;
- `PRC_INTVL_LMP`, version 3, RTM five-minute prices;
- `PRC_RTPD_LMP`, version 3, RTPD/FMM fifteen-minute prices;
- `PRC_AS`, version 12, DAM ancillary prices;
- `PRC_INTVL_AS`, version 1, RTM ancillary prices.

NP15, SP15 and ZP26 hubs are baseline context. Reviewed project nodes are added from the mapping inputs below. Ancillary reports request all published regions/service types, preserving source regional scope; this does not establish a project's eligibility or actual market participation.

The backfill job `caiso-backfill-2026-10-18` pins 72 existing batches/ZIP responses representing 8,640 component observations, plus an explicit 2021-01-01 through 2026-10-17 expanded collection scope. The pinned standard/archive boundary is 2023-07-01: older periods use the official historical downloader's search and requester-pays S3 objects; newer periods use SingleZip. Daily collection revisits the preceding seven completed Pacific days for corrections. The original regular collector remains the two-hub DAM component feed; expanded markets/nodes are in the dedicated outputs above.

Historical groups are `DAM_LMP`, `RTM_LMP`, `RTPD_LMP`, `DAM_PRC_AS` and `RTM_PRC_AS`. Listings are pinned per month with evidence; missing dates, duplicate keys and unexpected daily/hourly file counts are reported. The source bucket is `caiso-oasis-s3-prod-groupzips`, region `us-west-1`, using existing AWS credentials and `RequestPayer=requester`. Original response sizes, ETags, source last-modified times and requester charging metadata are preserved. Current-retrieved archive versions must not be described as historical public vintages. The requested scope starts in 2021, although the provider's archive extends farther back.

CAISO's historical website omitted its intermediate TLS certificate. `config/caiso-ca-bundle.pem` supplements existing trusted roots with the Sectigo intermediate verified against those roots. TLS/hostname verification remains enabled. Only official CAISO redirect hosts are accepted; AWS credentials are used by the SDK and never written to receipts or signed URL logs.

## Storage indicators and interpretation

Default analytical thresholds in `config/caiso-enrichment.json` are total LMP at least USD/MWh 200 for a spike and absolute congestion at least USD/MWh 50 for an episode. These are configurable research thresholds, not CAISO scarcity declarations or official price caps. Congestion episodes require contiguous intervals. Volatility is weighted by interval duration. Charge/discharge spread pairs respect chronological order and are labeled as unconstrained observed-price diagnostics.

`storage_revenue_estimate` stays null until documented asset efficiency, energy/power limits, duration, degradation, availability, dispatch constraints and applicable fees/settlement rules support an explicit model. No asset assumptions are invented and no spread is called realized revenue. Market conditions are separate from product performance, project income or financing outcomes.

## Project and RDS binding

Read RDS companies/products, attributes and relationships in one consistent TLS-protected, read-only snapshot. Configured `project_mappings`, and `tracking.products.attributes.caiso_projects` on verified, active energy-storage products, can provide the following reviewed mapping structure:

```json
{
  "project_id": "documented-external-project-identifier",
  "node": "DOCUMENTED_PROJECT_NODE",
  "node_type": "project_node",
  "review_status": "verified",
  "valid_from": "2025-01-01",
  "valid_to": null,
  "evidence": [{"source_url": "https://official-source.example/project", "document_sha256": "verified-document-sha"}],
  "relationships": [
    {"company_id": "cmp_<existing-RDS-ID>", "role": "operator", "review_status": "verified", "valid_from": "2025-01-01", "valid_to": null, "evidence": [{"source_url": "https://official-source.example/operator"}]},
    {"product_id": "prd_<existing-RDS-ID>", "role": "installed_product", "review_status": "verified", "evidence": [{"source_url": "https://official-source.example/installation"}]}
  ]
}
```

The placeholders illustrate the contract and are not real mappings. Evidence must document the specific project/node and each asserted relationship. Validity dates are checked at the price interval. Referenced RDS companies/products must be reviewed and active. Known hub nodes are rejected even if mislabeled as project nodes. Product ownership or geography alone does not establish project ownership, operatorship or installed equipment. Existing `product_companies` rows are not automatically promoted into project relationships.

RDS contained no companies, products or documented mappings at launch. Consequently project exposure output may correctly be empty; the worker does not guess links. Later daily jobs reread the registry. Reprocessing older history against newly reviewed mappings requires a separately versioned run, preserving the original backfill snapshot.

## Operations and completion email

`optima-caiso-backfill.timer` and `optima-caiso-daily.timer` resume bounded work approximately every five minutes. Both share a capture lock, process at most six archives and two monthly listings per invocation, and retry failures up to three times with a 30-minute delay. OASIS requests share host-wide five-second pacing with the regular collector. Daily work requires an exhausted, complete same-day parent capture and resumes unfinished prior daily jobs.

State is in `caiso-enrichment.sqlite3`, with local `reports/caiso-backfill-latest.json` / `reports/caiso-daily-latest.json` and S3 `operations/caiso-enrichment/jobs/{job_id}/`. Configuration, input inventory, directory snapshot, listing evidence, source bytes and per-output collection manifests provide reviewable provenance. Historical all-node archives require substantially more processing than targeted live queries; the final task count grows until all monthly listings are processed.

The completion email to `randall@optima-holdings.com` uses the existing confirmed SNS topic. It waits for catalog discovery to terminate, every input task to be complete or an explicit gap, every emitted batch to be verified by the committed Athena index, and exact source/job/version row counts. The message reports failed tasks, catalog and quality issues, mapping scope and the full completion receipt. Pending publication is not completion. Component/schema, interval coverage and missing-node issues remain visible even when source bytes were successfully captured.

Use the enriched queries in `ENTITY_DISCOVERY_ROLLOUT_PLAN.md#sql-checks`. They select extraction version `caiso-market-evidence-v1`; use the job ID above for backfill-only inspection.
