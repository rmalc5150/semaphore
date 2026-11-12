# CMS payments catalog and financial records — reviewed 11 November 2026

The single JSON document under `source_documents/cms_payments_catalog/` is the provider's dataset catalog. It contains descriptions and download links for many datasets. Repeated publisher, agency, contact, licence and year/category text is normal catalog structure, not repeated financial transactions. Identical catalog responses share a content-addressed raw object; daily observations can refer to the same object. Actual financial CSV files are archived separately under `research-data/cms-financial/files/<edition_id>/original.csv`.

CMS distinguishes its [dataset catalog](https://openpaymentsdata.cms.gov/api/1/metastore/schemas/dataset/items) from the [downloadable financial datasets](https://openpaymentsdata.cms.gov/datasets/download). The catalog metadata and the payment/spending records therefore have different Athena tables.

## What was repaired

- The metadata engine had stopped `cms_payments_catalog` because its generic JSON-content check did not recognize valid dataset descriptors. Contract **2.0.3** now checks original-response SHA256, official API origin, dataset UUID, publisher, complete descriptor equality, dataset URL and official download links. It labels these records `financial_dataset_catalog`, with a flag that they are not individual payments/spending rows.
- All four originally failed batches replayed successfully: **128 observations**. Requeued **16 unfinished committed catalog jobs** under the corrected contract. Public website discovery receipts remain archived and cannot stop the native catalog route. An older uncommitted attempt remains withheld by the existing commit checks; it is not published merely because its raw batch exists.
- A fresh November 11 capture saved **40 catalog descriptors**, passed both metadata continuation jobs, and was published in both the metadata and specialist curated tables. The original SQL now returns **168 observations / 5 linked batches**, all raw-complete. These are repeated observations over time, not 168 different financial datasets.
- Financial collection had been disabled during worker migration. Restored the exact checksummed original registry and its 20-file inventory, preserving completed work. The catalog runs on the worker; financial files run on the controller using its existing S3/Glue permissions. No IAM expansion was made.
- The first controller refresh exposed memory throttling in the shared data slice. Only the repaired CMS controller jobs moved to `optima-financial.slice`, capped at **384 MiB** and **30% CPU** together. The financial job has a **20% CPU**, 150-second work target and six-minute outer limit; individual file processing remains resumable. Other jobs were left running.
- New financial runs explicitly disable completion notifications. SQLite registry backups are consistent snapshots, checksummed and saved to S3 after runs. Catalog capture and financial ingestion have independent locks, logs and schedules.

## Verified availability

| Data | Athena table | Verified rows | Files/editions |
| --- | --- | ---: | ---: |
| Catalog descriptors | `optima_metadata_engine.source_observations`, source `cms_payments_catalog` | 168 observations | 5 linked raw batches |
| Detailed Open Payments | `optima_collected_data.cms_open_payments_rows` | **76,013,225** | 15 |
| Drug spending | `optima_collected_data.cms_drug_spending_rows` | **63,336** | 5 |
| Financial edition provenance | `optima_collected_data.cms_financial_editions` | 20 editions | 20 |

All 20 configured financial files are complete. At **15:25 Madrid time on November 11**, the automatic job verified exact per-edition Athena counts against committed CSV checkpoints, matched original checksum receipts, and checked archived file sizes. This did not re-download/re-hash every large original or rescan all payment IDs for uniqueness. The fresh verification receipt and registry backup are recorded in `live-status.json` and under:

- `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/cms-payments/verification/latest.json`
- `s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/cms-payments/registry/latest.json`

Actual `row_json` payloads were inspected in Athena for general payments (**91 fields**), research payments (**252 fields**), ownership (**30 fields**) and annual Part D spending (**46 fields**). Examples include manufacturer/recipient identities, payment amounts and drug/product mentions, ownership amounts, and branded/generic names with annual spending/utilization fields. Original strings, leading zeroes, decimal money and suppression markers are retained. Catalog descriptors are processed by the metadata engine; individual financial rows remain in their dedicated tables and are not represented as catalog observations.

**67 focused/regression tests passed.** Specialist tests use the checked-in example universe without changing runtime-managed symlinks. Both CMS metadata contracts/source processing and the metadata worker were checked online; all 15 historical worker services remained active. This is not a blanket certification of unrelated source validations.

## Schedules

| Step | Location and timer | Behavior |
| --- | --- | --- |
| Catalog capture | Worker `optima-cms-payments-resumed.timer` | Checks every five minutes after completion; refreshes the catalog once per day and directly enqueues metadata batches |
| Catalog publication | Controller `optima-cms-catalog-publication.timer` | One completed catalog window per run, continuing two minutes after completion; uses the common specialist publication lock/configuration |
| Financial files | Controller `optima-cms-financial-resumed.timer` | Checks every five minutes after completion; discovers editions daily, skips completed files and resumes any new/incomplete file |
| Financial reconciliation | Financial job | Once daily: per-edition Athena counts, original checksum receipts and archive sizes |

The old financial timer and disabled legacy route remain replaced by these explicit schedules. No owner-paused source was resumed.

## Your Athena checks

Use `AwsDataCatalog`, **us-east-1**. Your existing query is correct for catalog metadata and now returns rows:

```sql
SELECT source_key,
       count(*) AS observations,
       count(DISTINCT raw_s3_uri) AS linked_raw_objects,
       count_if(raw_completeness_status = 'complete') AS complete_raw_observations,
       min(ingested_at) AS first_ingested_at,
       max(ingested_at) AS latest_ingested_at
FROM optima_metadata_engine.source_observations
WHERE source_key = 'cms_payments_catalog'
GROUP BY source_key;
```

For the actual financial collections:

```sql
SELECT source, title, category, program_year, row_count,
       edition_id, raw_key, sha256, url
FROM optima_collected_data.cms_financial_editions
ORDER BY source, program_year, category;
```

```sql
SELECT count(*) AS payment_rows
FROM optima_collected_data.cms_open_payments_rows;
```

```sql
SELECT count(*) AS spending_rows
FROM optima_collected_data.cms_drug_spending_rows;
```

These sample queries return up to 20 random rows from the **first 5,000 rows of a specified edition**, keeping scans small. They are not random samples of the entire financial archive. All provider fields are in `row_json`; the four common table columns are `dataset_id`, `record_id`, `row_json`, `row_number`, plus the `edition_id` partition.

2025 general payments:

```sql
SELECT *
FROM optima_collected_data.cms_open_payments_rows
WHERE edition_id = 'e498c85722c5e04dbbe794286955c143b62b093a716a7e0886c8e1eb9d7f29e5'
  AND row_number BETWEEN 1 AND 5000
ORDER BY rand()
LIMIT 20;
```

2025 research payments:

```sql
SELECT *
FROM optima_collected_data.cms_open_payments_rows
WHERE edition_id = '20bc9efd094dc978a3f442fb85355e86f5c71582b3ca9b726b1f820c8c7ca8ff'
  AND row_number BETWEEN 1 AND 5000
ORDER BY rand()
LIMIT 20;
```

2025 ownership:

```sql
SELECT *
FROM optima_collected_data.cms_open_payments_rows
WHERE edition_id = '0f40012640b52dfac7053dca613ef1d860d76cf1f5620a297f06f5247d289787'
  AND row_number BETWEEN 1 AND 5000
ORDER BY rand()
LIMIT 20;
```

Annual Part D drug spending:

```sql
SELECT *
FROM optima_collected_data.cms_drug_spending_rows
WHERE edition_id = 'b6042c1020a29c2d4e8dfddc96d31daa3c486aeeae96c7f4218f59fefdd250e4'
  AND row_number BETWEEN 1 AND 5000
ORDER BY rand()
LIMIT 20;
```

To see payment fields directly, replace `SELECT *` in the general/research sample with:

```sql
SELECT record_id,
       json_extract_scalar(row_json, '$.Applicable_Manufacturer_or_Applicable_GPO_Making_Payment_Name') AS payer,
       json_extract_scalar(row_json, '$.Total_Amount_of_Payment_USDollars') AS payment_usd_as_supplied,
       json_extract_scalar(row_json, '$.Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_1') AS first_product_mention,
       row_json
```

Do not multiply a payment amount by its number of product mentions. Ownership, payments, annual/quarterly spending, overall/manufacturer subtotals and revised editions must be interpreted separately. Provider names and product mentions are not verified constellation entity links or company revenue allocations.

## Evidence and scope

- Original catalog query repaired: `4bf5ba1f-301f-4f48-9ec7-c14dcc6d9739` (`athena-verification.json`).
- Fresh metadata payload: `cec67bf4-2410-472b-9ccd-e91f822e425a`; native specialist payload: `05193fd5-0cd6-40f9-b97b-3da3fb6b07c4`.
- Actual financial counts: `66558c0b-5780-4f2e-8868-027e6d074e0d` and `43c3e4b6-3dec-4bec-beb2-da08bb640155`.
- Four financial sample results, scan sizes and exact SQL are saved as `sample-general.json`, `sample-research.json`, `sample-ownership.json`, `sample-drug_spending.json`. Each passed below the 100 MiB query guardrail.

**Reviewed for the configured scope; no action or API key is needed from you.** The completed financial scope is detailed General/Research/Ownership Open Payments for **2021–2025**, current annual Medicare Part B/Part D/Medicaid files with **2020–2024** value fields, and current quarterly Part B/Part D **2026 Q1** files. The refreshed catalogs still selected these 20 editions. This is not all-payer claims, every earlier archived release, historical publication vintages or resolved entity/product ownership. Future provider editions will be discovered automatically.
