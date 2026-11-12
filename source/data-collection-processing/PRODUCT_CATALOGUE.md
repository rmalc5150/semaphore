# Direct web product rebuild

The active initial population uses assistant-led direct web browsing and
`product_web_registry.py` to load explicitly researched manifests. It does not
call the OpenAI API. The former API discovery service is stopped.

The company filter is exactly:

```sql
WHERE review_status = 'verified'
  AND collection_enabled = 1
  AND archived_at IS NULL
```

The initial cohort snapshot and per-batch research manifests/receipts are in
`/home/ec2-user/product-web-rebuild/`. The initial snapshot contained 2,213
companies; eligibility is rechecked under a row lock before every write. New
company admissions can change the live count. Product relevance is separately
assessed against the four sectors; the company query adds no sector filter.

All previous product rows, dependent links and prior scan metadata were cleared
with user authorization, without a backup. Existing audit history is preserved.
The loader has no web-research or model call: the assistant supplies the reviewed
source URLs, product identities, company roles, aliases and supported contexts.
New product records/links remain pending review and collection disabled.
Historical relationships have explicit end dates when supported. Unresolved
portfolios stay partial; an attempted scan is never reported as exhaustive.
Cross-company name matches require explicit identity resolution rather than
automatic duplication. Research manifests are resumable without reinserting
products already linked to the same company under the same canonical name.

## Previous API implementation (inactive)

`product_catalogue_pipeline.py` researches products for nonarchived verified RDS
companies assigned to biotech, robotics, semiconductors, or energy storage. It is
separate from S65. New records remain pending review; collection stays disabled.

Research uses the existing company-catalogue OpenAI configuration. Its external
payload contains public company names, website URLs, sector labels, existing
public product names, and the public taxonomy. It excludes internal company IDs,
review states, database credentials, and company evidence documents.

Official source pages are independently fetched and exact name/fact quotes checked.
Sources and research receipts are archived in S3. Ambiguous matching identities
and unsupported roles are rejected for review. Existing reviewed values are
preserved; only missing descriptive values and unknown lifecycle are enriched.
Contexts, aliases, identifiers, and family hierarchies need separately supported
reconciliation; they are not guessed.

`product_catalogue_migration.py` adds UTC `last_product_scan_at`, outcome
`last_product_scan_status` (complete/partial/failed), `last_product_scan_error`,
and JSON `last_product_scan_evidence`. The time records a completed attempt,
including failure; check the outcome to distinguish success. A supplemental audit
trigger records scan field changes on upgraded databases. Existing actor, reason,
UTC, and version checks remain active.

Product writes and scan outcomes commit together after verification/version
rechecks under a row lock. A database advisory lock prevents concurrent discovery
workers. Failed writes roll back; provider errors stop a batch. Unscanned verified
companies go first; partial/failed scans can retry after one day. Complete scans
are skipped unless explicitly requested. Empty or blocked results remain partial,
not evidence of an empty portfolio. Large portfolios may require further passes.

Use `.venv-athena/bin/python product_catalogue_pipeline.py` with
`--max-companies`, `--max-seconds`, and optionally `--company-id`.
Tests: `.venv-athena/bin/python -m unittest test_product_catalogue`.

The explicitly authorized initial sample was deleted by its ten IDs, with a backup
and original audit history retained. No other product identities were targeted.

`product_catalogue_backfill.py` drains the unscanned verified-company backlog in
bounded worker batches, writing a progress summary to
`research-data/operations/product-catalogue/backfill-state.json`. It is a one-off
backfill and exits after the initial pass; partial/failed companies are reported
separately. A failed worker stops the backfill so external provider failures do
not cause repeated paid requests. The worker supports `--replay-last-research`
with `--company-id` to revalidate an archived response without a new API call.
