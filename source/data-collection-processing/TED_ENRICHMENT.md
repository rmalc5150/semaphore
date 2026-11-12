# S42 linked XML enrichment

The ongoing TED adapter fetches each linked official XML before sealing a notice.
The original metadata remains in `payload.data`; successful enrichment adds
`notice_xml` and `enrichment`. Raw bytes are independently archived under
`source_documents/ted_notices/` with SHA256 and retrieval evidence.

`enrichment` retains the namespaced XML tree, attributes, ordered children and
path-indexed text, plus source date/value/reference/party field candidates.
Legacy TED forms and UBL roots provide conservative notice-stage classification.
A contract-award notice alone does not establish a successful award. Unrecognized
stages remain unknown. Amounts retain strings, currencies and lot context.
Specialists must resolve parties, distinguish estimated/awarded values, inspect
award outcomes, and link procedures/notices/lots before drawing conclusions.
No automatic entity resolution or historical-availability promotion occurs.

Backfill: `config/ted-enrichment-backfill.json` pins the 237 indexed S42 batches
(17,896 observations) present at launch. The hash-checked inventory is in
`reports/ted-enrichment-backfill-2026-10-18/input-batches.json`.
Repeated observations of unchanged metadata are grouped; metadata revisions and
parent observation/batch lineage are retained. Original rows are never overwritten.
One current XML retrieval may represent repeated historical metadata observations;
it is not a reconstructed historical XML vintage.

The enabled system timer `optima-ted-enrichment-backfill.timer` resumes work every
five minutes. Three consecutive retrieval failures defer the provider for six
hours. After five attempts a notice becomes an explicit gap. Empty/202 responses,
wrong notice identities, HTML, DTD/entities and untrusted download links cannot
be treated as successfully enriched XML. Requests use a generic client identifier.

Progress: `reports/ted-enrichment-backfill-2026-10-18-latest.json` and the matching
SQLite registry. Durable operational state and gap receipts are also stored under
`operations/ted/enrichment-backfill/ted-enrichment-backfill-2026-10-18/`.
The existing committed-Athena publisher registers output. Completion email uses
the existing confirmed email topic, checks its recipient, and waits for all pinned
versions to be processed and exact job row counts verified in Athena. Gap counts
and receipts are included; a finished run with gaps is not full XML coverage.

Select the latest observation before filtering readiness, so a failed latest
retrieval cannot silently fall back to older enriched observations:

```sql
WITH ranked AS (
  SELECT *, row_number() OVER (
    PARTITION BY source, dataset, source_record_id
    ORDER BY ingested_at DESC, observation_id DESC
  ) AS rn
  FROM optima_collected_data.observations
  WHERE source = 'ted_notices' AND dataset = 'specialist_inputs'
)
SELECT source_record_id,
       json_extract_scalar(payload_json, '$.data.enrichment.stage') AS notice_stage,
       payload_json
FROM ranked
WHERE rn = 1
  AND json_extract_scalar(payload_json, '$.data.enrichment.specialist_ready') = 'true';
```

Validation: `python -m unittest test_ted_enrichment test_ted_enrichment_backfill test_specialist_inputs -q`.
At launch the live linked XML endpoint returned empty HTTP 202 responses. Synthetic
legacy/UBL parsing and persistence tests passed; live end-to-end enrichment remains
unverified until the provider returns valid XML.

## Daily package retrieval (October 18 update)

Daily S42 discovery projects `ojs-number` and uses the official daily package
`https://ted.europa.eu/packages/daily/{year}{issue:05d}` as its primary XML source.
Daily job scopes changed only for S42 so earlier metadata-only completed jobs do
not prevent the updated daily scope from running. Discovery still covers the four
configured CPV categories with a seven-day lookback, not the entire TED universe.

`ted_packages.py` streams downloads to a temporary disk file, indexes regular XML
members without filesystem extraction, and caches compressed XML in a per-issue
SQLite file. Size/member/expansion limits and SHA256 validation guard truncated or
conflicting content. A per-issue process lock prevents duplicate concurrent
package downloads. Cache pruning removes old unlocked packages and targets a
512 MiB budget before each fetch (an active new package can temporarily exceed
that target). Extracted XML and archive provenance remain in durable S3 evidence
when the local cache is pruned. Older observations can resolve their missing OJS
number through an exact-ID API lookup. Individual-download failures automatically
fall back to the same package path for historical enrichment too.

Unavailable daily XML raises `ted_daily_xml_pending`, leaves the task partial and
the page cursor unadvanced, and defers the source for 30 minutes. The existing
hourly daily-collector timer resumes it. Incomplete jobs are retained outside the
moving seven-day discovery window. Missing notices, invalid XML and unpublished
packages cannot silently become completed metadata-only daily records.

Live verification used the original sample, not a newly published notice:
API discovery -> daily package `202100126` -> `20210702_126/331738_2021.xml` ->
21,490 XML bytes -> `award_notice`. Evidence and the archive SHA256 are recorded
in `reports/ted-daily-xml-live-verification-2026-10-18.json`. The modern root and
namespace parsing path is covered by fixtures; live current-day publication and
package-release timing have not been independently verified.

Validation includes `test_ted_packages` in addition to the tests above.
