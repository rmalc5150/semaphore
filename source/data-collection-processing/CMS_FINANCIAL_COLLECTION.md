# CMS financial files and backfills

**Restored and verified 11 November 2026:** the active financial timer is now **`optima-cms-financial-resumed.timer`** on the controller, using `config/cms-financial-controller.json` and `state/cms-financial/registry.sqlite3`. Daily catalog capture runs on worker **`optima-cms-payments-resumed.timer`**; catalog publication runs on controller **`optima-cms-catalog-publication.timer`**. The old financial timer/legacy route remains disabled. CMS controller jobs share a capped 384 MiB slice. Completion notifications are disabled for the resumed job. The preserved 20 editions are complete: **76,013,225 payment rows** and **63,336 spending rows**. Exact per-edition counts, original-file sizes and checksum receipts passed automatic verification; new editions remain automatically discoverable. See [current evidence and SQL](repair-notes/2026-11-11-cms-payments/README.md). The original setup below describes the initial implementation; its old timer/state-file references are superseded by this paragraph.

Configured October 16, 2026. This pipeline downloads the actual source CSV files, archives them in S3, and exposes their complete rows as Parquet tables in `optima_collected_data`. The existing `cms_payments_catalog` remains a discovery catalog; these new tables supply underlying records.

## Collections and initial scope

| Collection | Pinned files | Interpretation |
|---|---|---|
| Open Payments | 15 detailed CSVs: general, research and ownership records for each program year 2021–2025 | Reported financial relationships and ownership/investment interests, not drug sales or insurance reimbursement. |
| Annual drug spending | Medicare Part B, Medicare Part D and Medicaid, current 2024 editions | Published rolling 2020–2024 spending/utilization fields; retains the source's full contents. |
| Quarterly drug spending | Current Medicare Part B and Part D 2026 Q1 editions | Supplemental quarterly context, kept separate from annual data. |

This is a backfill of the pinned, currently published files, not reconstruction of every historical release or every claim. It does not supply all payer spending or net manufacturer revenue. The annual 2025 spending edition was not in the discovered catalog at launch. Future catalog discovery adds new editions; it does not invent missing years. Earlier Open Payments years and older quarterly file releases are outside this pinned backfill.

Official metadata: [Open Payments](https://openpaymentsdata.cms.gov/api/1/metastore/schemas/dataset/items), [CMS data catalog](https://data.cms.gov/data.json). Initial file inventory: [20 editions](reports/cms-financial-backfill-2026-10-16/input-editions.json). Original download URL, dataset identity, category, temporal metadata and dictionary URL are retained per edition. The dictionaries are referenced, not claimed to be downloaded by this worker.

## Operation

- Code: `cms_financial_collection.py`; config: `config/cms-financial-collection.json`.
- `optima-cms-financial-collection.timer` resumes work every five minutes after the prior invocation ends; catalog refresh occurs at most daily. One lock prevents overlapping writers. Completed editions are skipped.
- Each invocation targets nine minutes of work, with a 12-minute external timeout and the repository's 512 MiB / 40% CPU service limits. Individual requests and whole-file SHA256 verification can extend beyond the internal budget; the external timeout remains the hard limit.
- Large files stream into S3 multipart uploads in 16 MiB parts. Stable ETag/Last-Modified validation prevents mixed source versions. Where CMS ignores range requests, retries replay the source stream and skip committed bytes. No multi-gigabyte local CSV cache is required.
- Processing reads the archived original, computes SHA256, validates CSV headers, and checkpoints consumed byte boundaries and row counts. UTF-8, quoted newlines and source number strings are retained. Parquet is written in 5,000-row chunks. Deterministic chunk names permit replay after an interrupted upload.
- A file's row partition is registered only after complete parsing; its JSON manifest provides raw-file size, SHA256, source provenance and row count. No invalid or inaccessible file is silently marked complete. Errors remain in the status report and retry on subsequent invocations.
- Full source rows are retained as `row_json`; IDs, NDCs and monetary values remain original strings. This avoids floating point rounding, loss of leading zeroes and converting suppressed values into zero. Apply explicit decimal casts when analyzing amounts.

Local progress: `cms-financial-backfill-2026-10-16.sqlite3`. End-of-invocation status: `reports/cms-financial-backfill-latest.json` and S3 `research-data/cms-financial/status.json`. During an active invocation the SQLite checkpoints and service journal are more recent than the summary. Source files, Parquet chunks, manifests and completion receipt are under `s3://data-collection-059416028963-us-east-1-an/research-data/cms-financial/`.

## Athena access

These are dedicated tables, not new rows in the shared `observations` view:

| Table | Contents |
|---|---|
| `cms_financial_editions` | One manifest per completed edition, including title, category, source, edition/dataset IDs, program year, raw key, SHA256, row count and modified/published times. |
| `cms_open_payments_rows` | Full general, research and ownership CSV rows as JSON, with provider record identity, dataset ID, row number and edition partition. |
| `cms_drug_spending_rows` | Full spending CSV rows as JSON, with dataset ID, source-row identity, row number and edition partition. |

A source-row identity for spending is a provenance key within that edition, not an external drug ID. Payment record identity includes program year, category and CMS Record_ID. Corrected editions retain earlier files and rows: select one edition per dataset before aggregating. The SQL review queries show a latest-edition pattern; consult the file title/program/period to avoid overlapping datasets or annual/quarterly values. No query here implies historical availability.

Use `json_extract_scalar(row_json, '$.Total_Amount_of_Payment_USDollars')` for general/research amounts when that column exists, and `try_cast(... AS decimal(38,2))` for arithmetic. Ownership uses different fields, such as `Total_Amount_Invested_USDollars` and `Value_of_Interest`; do not sum ownership valuations with payments.

Drug spending fields vary by program and period. For the annual Part D file, `Tot_Spndng_2024`, `Brnd_Name`, `Gnrc_Name` and `Mftr_Name` are examples. `Mftr_Name='Overall'` identifies aggregate rows in this edition: avoid adding manufacturer subtotals to those aggregates. Read the appropriate program's methodology before comparing Part B, Part D and Medicaid. Gross spending is not net manufacturer revenue or an all-payer market estimate. Preserve suppression/outlier indicators and population/time definitions.

## Completion email

The confirmed destination is `randall@optima-holdings.com` through the existing SNS email topic. A single combined completion signal covers all 20 pinned files. It waits until:

1. All initial originals have been archived and completely parsed.
2. Athena counts match the recorded parsed count separately for every edition, and record IDs are unique within each edition.
3. Archived file sizes still match the receipts; SHA256 values are retained in the completed manifests.

The email includes exact edition counts and scope. A failure leaves the job pending and visible rather than sending success with omitted files. Future editions continue to collect after this backfill email. Email delivery uses SNS; a message ID records SNS acceptance, not proof that the recipient opened it. An interruption exactly between SNS acceptance and saving that message ID could repeat the notification on retry.

## Entity and product interpretation

Raw payment parties, recipient/profile identifiers, products, investigators, category and dispute flags remain available in the original rows. Company, person and product IDs are not automatically assigned. Research payments are not necessarily personal income to a named principal investigator. A reported payment can reference multiple products without allocating its amount among them; never count its full value against every named product.

The product and people population plans define the subsequent reviewed links. Neither a payment nor a reported ownership interest proves employment, an endorsement, misconduct, independence or product effectiveness. Keep financial facts separate from interpretation and from coverage policies in S32.

## Validation and recovery

`test_cms_financial_collection.py` checks dataset selection, source host validation, multiline/UTF-8 byte resume, exact money/suppression strings, malformed rows, year checks, deterministic Parquet replay, source-version changes, stream fallback and notification gating. Live launch verification is recorded in `reports/cms-financial-backfill-2026-10-16/launch-athena-verification.json`.

For an error inspect `journalctl -u optima-cms-financial-collection.service` and the edition's SQLite state. Restarting the service resumes recorded uploads/chunks. Do not delete its SQLite checkpoints while multipart uploads are in progress. A changed remote file under the same metadata identity is rejected for investigation; do not bypass version validation or combine old and new bytes. Use a new source edition after validating its provenance. Pending retries are not proof of completeness.
