# NIH, NIST, federal awards, TED and patents — review, 11 November 2026

The source queries now return actual Athena records. Generic raw validators had rejected valid original API responses; metadata jobs then stopped before publication. Added source-specific identity/content validation and replayed the saved batches under contract 2.0.3.

This is verification of the stated source/dataset pipelines and representative payloads. Historical completion, exhaustive issuer/universe coverage, entity resolution and readiness of every specialist feature remain separate checks.

## Verified Athena snapshot

| Source | Observations | Linked collection batches | Raw-complete rows |
|---|---:|---:|---:|
| `nih_reporter` | 2830 | 46 | 2830 |
| `google_patents_bigquery` | 2608 | 11 | 2608 |
| `uspto_odp` | 1859 | 60 | 1859 |
| `uspto_assignment_histories` | 131 | 60 | 131 |
| `ted_notices` | 2323 | 77 | 2323 |
| `usa_spending` | 1703 | 83 | 1703 |
| `nist_robotics_methods` | 130 | 130 | 130 |
| `nist_robotics_documents` | 75 | 75 | 75 |

Counts are row occurrences over captures, snapshots and content chunks, not unique grants, patents or awards. `raw_s3_uri` names the committed collection envelope; original API/XML/PDF references and checksums are in `labelled_json.raw_artifacts`. The query ID and full response are in [counts.json](counts.json).

## What was checked

- **NIH RePORTER grants:** Complete returned NIH project-application records: grant IDs, project numbers, title/abstract, amount, organisation and investigators. Configured topics/organisation candidates; grant proposals and historical API vintages remain separate. One October 9 batch lacks its commit checkpoint and remains uncommitted, with raw files retained.
- **Google Patents BigQuery:** Verified bibliographic exports, original completed BigQuery result pages, provider identifiers and typed schema. Patent claims/specification/full text remain uncollected by this route; this review covers the bibliographic pipeline only.
- **USPTO Open Data Portal:** Verified application bibliography, normalized assignment ledgers, office-action text with original PDFs, and petition-decision PDFs, separately by dataset. Candidate entity links and current legal title remain unverified. Approved application/document exclusions are retained and excluded from full-document observations.
- **USPTO assignment histories:** Recorded assignment events and the complete returned chain for the eight configured applications. Recorded deed images, all USPTO assignments and legal/current ownership are separate coverage requirements.
- **Tenders Electronic Daily procurement notices:** Original notice XML, complete parsed XML trees and provider search metadata for configured CPV scopes. Oversized notices retain ordered content chunks; chunks are not additional notices or awards. The fresh verified notice is 768246-2026. XML retrieval gaps remain separately retryable.
- **USAspending federal awards:** Complete returned selected award-summary fields for named-universe contract candidates. Grant/loan programmes, all recipients, full transactions and full award dossiers are outside this configured route.
- **NIST robotics methods:** Original NIST robotics pages and a fresh 19-page grasp-performance study PDF with 6,713 extracted text characters. Discovery/project/method/PDF kinds remain explicit. Companion documents use nist_robotics_documents. Graphics, measurements not present in extracted text and historical website vintages are not inferred.

Inspected actual provider payloads, not only status rows or counts. Evidence: `sample-<source>.json`, `fresh.json`, `nist-method-pdf.json`, `odp-datasets.json`, the replay receipts and deployment manifests in this folder.

## Ongoing processing

Daily specialist capture: `optima-grants-reviewed-capture.timer` (five-minute continuation). NIH historical capture: `optima-nih-reviewed-historical.timer` (ten-minute continuation). TED/USAspending retain their independently scheduled historical routes. Assignments use the existing authorised controller role with separate daily/historical timers.

Google historical and USPTO daily/historical continuation use `optima-patents-reviewed-{google,odp,odp-historical}.timer` (15 minutes). Existing Google per-query and daily billing ceilings remain unchanged. Google is currently collecting historical bibliography; a complete, current global patent-text feed is not verified. NIST retrieves current original documents; older publication dates are not reconstructed historical website snapshots.

Metadata has separate per-source leases, a maximum of two additional workers and bounded batches. `optima-reviewed-metadata-continuation.timer` and `optima-reviewed-metadata-publication.timer` keep these queues moving alongside the general engine. Individual failures retain reports and retry independently. Native specialist publication uses `optima-grants-reviewed-publication.timer`.

A sustained background check exposed slow queue SELECTs and incorrect probe lock ownership. Added online covering indexes, candidate-ID selection, primary-key fetches, ten-second query/lock limits and preservation of the original error if rollback fails. See `database-queue-repair-proposal.md`, `queue-indexes-after.json` and operational verification receipts.

## Your checks

No new API key, account or permission purchase is required for these configured routes. Open Athena in `us-east-1`, workgroup `optima-collected-data`, and run the source count checks in the main review schedule. Use the bounded examples below to inspect the complete saved metadata columns and original payload.

### NIH RePORTER grants

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'nih_reporter'
  AND job_id IN ('913396f48bf17a6684d9b82020a1de4749b7e23cd1cf73f8136f71748ab35764')
ORDER BY rand()
LIMIT 20;
```

### Google Patents BigQuery

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'google_patents_bigquery'
  AND job_id IN ('33b5a60d31fbb52e61a7ab002224d98f11ca014fc1686aac941ddf90480b0886')
ORDER BY rand()
LIMIT 20;
```

### USPTO Open Data Portal

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'uspto_odp'
  AND job_id IN ('adca32d86216319238d4f8e6467e315be74e754c46a1d5df955d864023445a5f', '50ac50d00ca72dbab462c451d4d756576cc39160ea821bcbe7dac380cbb5cd53', '1533dbcaeb7254389aeb281a858dc1981f5dd547345d3fea2acfbc7c8f5c4879', '72f40fba1c1fd0cba430046897a00892306bce3b3f09dabc57b269656059051c')
ORDER BY rand()
LIMIT 20;
```

### USPTO assignment histories

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'uspto_assignment_histories'
  AND job_id IN ('10fb8435d0159ed54a54df61ffe606fa919b124c7edd0e8da24210878387ea92')
ORDER BY rand()
LIMIT 20;
```

### Tenders Electronic Daily procurement notices

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'ted_notices'
  AND job_id IN ('79db732e0c3815d69b747f875dfd5bfc4cc616d072fda2e5e174fae07e86be99')
ORDER BY rand()
LIMIT 20;
```

### USAspending federal awards

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'usa_spending'
  AND job_id IN ('ab9ea776b2509ddd87549d9e66c2ea3faf5fa55ea7694c56aaa80e6c4996ca99', '499166884016aade62f445dae59f30982c5d48c60fb69ada7f94845866eae0b1', 'f09ba272fb055d092c45456c86db3b303bc1ef18ee895884b57e6ef951a49665')
ORDER BY rand()
LIMIT 20;
```

### NIST robotics methods

```sql
SELECT *
FROM optima_metadata_engine.source_observations
WHERE source_key = 'nist_robotics_methods'
  AND job_id IN ('a665c068b995b4ac142725aa181f6cb93c392185d3154a8c1ccd9d32880ea808', '00b54560fee1f0bb182149a779887a675390ba5e3a999b9b28ef5edb2dcc496c')
ORDER BY rand()
LIMIT 20;
```

Payload fields are in `json_extract(labelled_json, '$.payload.data')`; original artifacts are in `json_extract(labelled_json, '$.raw_artifacts')`. These small sample partitions can return fewer than 20 rows. A snapshot review does not certify the whole historical archive.
