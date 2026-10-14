# Patent landscape pilot

This is the legacy 20-company pilot. For the shared-universe migration, S3
ingestion and historical/daily commands, use [PATENT_COLLECTION.md](PATENT_COLLECTION.md).
Its `patent_discovery.sql` and `patent_query_plan.py` replace the fixed-company
query for future global exports. Legacy event output is not model-ready.

This pilot discovers public patent applications and grants belonging to a
curated company universe, then classifies the technology independently of the
company's industry. It intentionally reports public records, not confidential
or unpublished filings.

## Inputs

- `patent_pilot_companies.json`: 20 initial companies (five per sector) and
  known applicant/assignee aliases. Review ownership and historical aliases
  before treating the results as complete.
- `patent_bigquery.sql`: discovery query for
  `patents-public-data.patents.publications`.
- BigQuery parameters `start_date` and `end_date`, both typed as `DATE`.

The seed set favors focused or strategically important companies. It is a
pipeline-validation sample, not an investable or comprehensive company list.

## Run

1. Create a Google Cloud project and enable BigQuery.
2. Run `patent_bigquery.sql` with a bounded date range. Start with one year.
3. Export the result as newline-delimited JSON, for example `patents.jsonl`.
4. Normalize and classify it:

   ```bash
   python patent_landscape.py patents.jsonl --output patent_review.jsonl
   ```

The output retains source fields and adds `matched_company`, `company_sector`,
`technology_classifications`, `target_sector_match`, and `review_required`.
The discovery pass intentionally omits abstracts because scanning that large
column makes even narrow date-range queries expensive on the unpartitioned
public table. Abstract enrichment should be limited to the matched publication
numbers in a later step.

## Pilot acceptance checks

- Manually inspect at least 25 records per sector, including all low-confidence
  records.
- Measure company-match precision and technology precision separately.
- Group results by `family_id` before portfolio counts; preserve document-level
  rows for jurisdiction and prosecution work.
- Check at least ten known patents per sector to estimate recall.
- Record the query date, CPC scheme version, source table update time, and query
  bytes billed for every run.

## Next connectors

`uspto_patents.py` collects raw application data from the
[USPTO ODP application endpoint](https://data.uspto.gov/apis/patent-file-wrapper/application-data).
It retrieves its API key at runtime from the `USPTO` Secrets Manager secret:
`arn:aws:secretsmanager:us-east-1:059416028963:secret:USPTO-CwTvy4`.
The AWS execution role needs `secretsmanager:GetSecretValue` on this secret.
Store the key as plain text or a JSON object with `API_KEY`, `USPTO_API_KEY`,
`x-api-key`, or `USPTO`. No key is stored in source code or output.

```bash
python3 uspto_patents.py 16123456 --output uspto_applications.jsonl
```

Replace the example number with your target's eight-digit application number.
Use `--secret-id` (or `USPTO_SECRET_ID`) and `--region` to override configuration.
Output contains raw ODP responses; normalize these before supplying them to
`patent_events.py`. The BigQuery workflow below remains the discovery source.

After validating discovery, enrich each record by publication/application
number with USPTO Open Data Portal data for US application status, assignments,
and file-wrapper documents, and EPO OPS for worldwide family and legal-event
verification. Credentials and rate-limit handling should be added at that
stage; browser scraping is not required for this pilot.

## Daily events

`patent_events.py` compares the latest normalized JSONL snapshot with the prior
snapshot and writes a versioned event envelope. Event IDs are deterministic, so
downstream ingestion can use `eventId` as its idempotency key.

```bash
python3 patent_events.py current.jsonl --previous previous.jsonl \
  --date 2026-09-14 --source uspto-odp --output patent_events_2026-09-14.json
```

On the first run, omit `--previous` to establish state without generating
hundreds of historical alerts. Add `--emit-bootstrap-events` only when a full
historical event backfill is intentional.

Supported normalized transitions are application publication, grant
publication, status change, pending-to-granted transition, and assignee change.
No source can emit an event for a still-confidential filing. BigQuery is the
periodic global discovery/backfill source; USPTO ODP and EPO services should be
the operational status/publication sources at their actual update cadences.
