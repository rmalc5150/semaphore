# Five FDA feeds — repaired and reviewed 11 November 2026

All five original SQL queries now return rows. The common cause was metadata processing stopped at `missing_verified_raw_artifacts:provider_record`: the generic content validator did not recognize the FDA-specific records/envelopes, although original API responses were saved.

Contract **2.0.3** now verifies each source's official host and endpoint, original SHA256, API response shape/counts, complete returned row, record identity and requested date scope. Dashboard composite identities preserve distinct citations within the same inspection; iRES preserves product IDs and all returned selected fields; PCB table columns/row widths and complete industry-reference count are checked. No raw objects were deleted or rewritten.

FDA's API-level `statuscode`/`STATUSCODE`/`APIRETURNCODE` value **400** denotes success for these responses; it is separate from the HTTP status. Saved tabular PCB responses use `COLUMNS`/`DATA` rather than the Dashboard's `result` list. The source-specific validators handle both structures.

## Verified Athena snapshot

| Feed | Source key | Metadata observations | Linked raw batches | Fresh verification records |
| --- | --- | ---: | ---: | ---: |
| FDA Enforcement Report recalls | `fda_ires_recalls` | 179 | 4 | 51 |
| FDA Dashboard inspection citations | `fda_dd_inspections_citations` | 195 | 6 | 35 |
| FDA Dashboard compliance actions | `fda_dd_compliance_actions` | 162 | 6 | 2 |
| FDA Dashboard import refusals | `fda_dd_import_refusals` | 425 | 8 | 265 |
| FDA product codes — industry reference | `fda_product_codes` | 217 | 4 | 89 |

All listed observations are raw-complete for their declared API scope. Counts include repeated observations over capture dates; they are not unique entities, unique events or completed archive counts. Fresh ingestion was verified on November 11, around **15:45–15:48 Madrid time**. The five freshly captured windows contain **442 records**, all checked against the original responses, published and queried in both destinations:

- `optima_metadata_engine.source_observations`: provider records under `labelled_json` → `$.payload.data`; source context under `$.payload.fda_context`.
- `optima_specialist_inputs.source_observations_windows`: original normalized source payload under `payload_json` → `$.data`; bounded by `window_id`.

The actual inspected native payloads included all five sources, with matching provider fields: action type/date, FEI/firm names; shipment/product/refusal charges; inspection/citation/CFR descriptions; recall numbers/product descriptions/reasons/dates; and industry IDs/descriptions, preserving code strings and nulls.

## Repairs and operation

- Validated **20 previously failed job inputs** and replayed **18 distinct batch jobs**. The iRES and PCB failures included duplicate historical job identities referring to the same input; those coalesced under the new contract. Requeued **599 unfinished native jobs** across the five sources. Each source has its own fenced replay script/service and durable metadata attempt reports.
- Both the source registry and metadata workers use date-specific failure handling: later bad windows are recorded without stopping the source. All five sources were **enabled with zero consecutive raw failures** at the final check. Metadata/publication catchup remains queued.
- Live Dashboard and iRES access passed from the production worker. The worker lacked access to the PCB credential; the industry-reference collector now runs on the controller using its existing access. No new key or IAM expansion was needed, and the obsolete worker authenticated lane no longer attempts that credential.
- Worker `optima-fda-reviewed-capture.timer` continues two minutes after completion. It rotates among the four Dashboard/recall sources, attempts at most two scopes per run, retains page checkpoints, limits each scope, and records failures/cooldowns separately. This worker handles daily lookback refresh; the existing isolated historical routes remain independent and enabled.
- Controller `optima-fda-product-codes-capture.timer` continues five minutes after completion and captures the current industry reference once per daily scope. No historical code vintages are invented.
- Controller `optima-fda-reviewed-publication.timer` continues two minutes after completion, publishing two completed FDA windows per run under the existing specialist publication contract/lock. Partial captures may enter metadata as committed records, but they are not advertised as completed native coverage windows.
- Controller jobs use the existing capped `optima-financial.slice`; worker capture has a 384 MiB / 20% CPU limit. Individual failures do not stop the other feeds. The metadata timer and all **15 historical worker services** were checked active; this does not certify unrelated source contents. Owner-paused sources remain paused.

**66 focused/regression tests passed.** Specialist tests used the checked-in example universe without replacing runtime-managed `/dev/shm` symlinks. `metadata-deployment-result.json`, `health-result.json`, per-source replay reports, `fresh-validation.json` and `fresh-receipts.json` hold the evidence.

## Important scope limits

**Product codes:** the configured `/rest/pcbapi/v1/industry/` route returns **89 industry IDs/descriptions**. It does not collect all five components of the Product Code Builder hierarchy, all seven-character combinations, or the separate device-classification taxonomy. Metadata explicitly labels it `industry_reference` with `full_five_component_taxonomy=false`.

**Recalls:** the inherited collector requests eleven named business columns plus the server's `RID`. Those returned fields are retained completely and flagged using `legacy_selected_columns=true`; this flag also applies to fresh captures made with that inherited request format. This is not a full recall case-file or all-fields claim. Scope selection uses **event modification date (`eventlmd`)**, which differs from recall-initiation date; overlap with openFDA remains separate.

**Dashboard:** the API returns complete selected-dataset rows with `columns: []`. These are not original 483 forms or warning-letter documents. FEI, firm names and product references are retained but remain unresolved constellation identities. Current source revisions are not historical publication vintages.

These sources are reviewed for those configured feed scopes. This does not mark the whole historical archive, metadata catchup, downstream entity mapping or specialist feature engineering complete.

## Athena checks

Use `AwsDataCatalog`, **us-east-1**. Your existing single-source queries work unchanged. A combined check is:

```sql
SELECT source_key,
       count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM optima_metadata_engine.source_observations
WHERE source_key IN (
  'fda_dd_compliance_actions',
  'fda_dd_import_refusals',
  'fda_dd_inspections_citations',
  'fda_ires_recalls',
  'fda_product_codes'
)
GROUP BY source_key;
```

FDA Dashboard compliance actions:

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'fda_dd_compliance_actions'
ORDER BY rand()
LIMIT 20;
```

FDA Dashboard import refusals:

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'fda_dd_import_refusals'
ORDER BY rand()
LIMIT 20;
```

FDA Dashboard inspection citations:

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'fda_dd_inspections_citations'
ORDER BY rand()
LIMIT 20;
```

FDA Enforcement Report recalls:

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'fda_ires_recalls'
ORDER BY rand()
LIMIT 20;
```

FDA product codes — industry reference:

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'fda_product_codes'
ORDER BY rand()
LIMIT 20;
```

All provider fields are in `labelled_json` → `$.payload.data`. These random queries scan the selected source; their current scans are small, but `LIMIT` does not bound future scan cost. For a fixed native window, use a verified `window_id` from `fresh-windows.json`, which retains the manifest/source mapping, and query:

```sql
SELECT *
FROM optima_specialist_inputs.source_observations_windows
WHERE window_id = 'a45a3049e1d3f31b11ca3bfae4482923af9feffc3429d4e5eb47657263e30ea2'
  AND source = 'fda_dd_import_refusals'
ORDER BY rand()
LIMIT 20;
```

That partition contains the verified 265-row refusal window. The other proof windows contain 2 actions, 35 citations, 51 recalls and 89 industry-reference rows; a `LIMIT 20` query returns fewer rows when the selected window contains fewer.

## Query evidence and your next step

- Final metadata counts: `9d8c115a-0a4f-47cc-b325-e96ee4229f3b` (`counts.json`).
- Five native counts: `8695d640-cb31-4bd0-83f7-785b1e262381` (`native-counts.json`).
- Actual native payloads from all five sources: `a44ba722-f309-4fa1-be6d-3ccb3b0a5eed` (`native-payloads.json`).
- FDA Dashboard compliance actions metadata sample: `0184ae80-bb1e-4bcc-9174-b8149e7bee98`.
- FDA Dashboard import refusals metadata sample: `b0083db5-d4c4-4175-aae3-7a98b2f2de32`.
- FDA Dashboard inspection citations metadata sample: `4a314927-8017-430c-bcbd-1845a437ad15`.
- FDA Enforcement Report recalls metadata sample: `7f8facbd-4dcf-483d-b87e-ec6c2e91e88a`.
- FDA product codes — industry reference metadata sample: `c1854b50-35f9-4670-8d79-27992ed5b3cb`.

**No new API key, account setup or manual restart is needed from you.** You can continue the optional Athena spot checks above. The original Dashboard inspection-classifications entry (#35) was outside this five-source request and was not marked reviewed.

Official API scope/response documentation: [FDA Dashboard](https://datadashboard.fda.gov/oii/api/index.htm), [Enforcement Reports](https://www.accessdata.fda.gov/scripts/ires/apidocs/), [Product Code Builder](https://www.accessdata.fda.gov/scripts/ora/pcb/apidocs/).
