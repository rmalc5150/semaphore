# FDA openFDA — November 10, 2026

Entry 17 is reviewed after original-provider validation, live API probes, production replay and Athena checks. No new key or owner access step is required. Review covers structured application/submission and CRL API records, not every linked PDF or all historical periods.

## Root cause and repair

The metadata contract 2.0.2 had an empty provider-host allowlist. Four saved API batches failed `missing_verified_raw_artifacts:provider_record`, stopping metadata processing although the raw responses existed.

Added `metadata_engine/openfda.py`, official `api.fda.gov` endpoints and immutable contract 2.0.3. Approval validation requires the entire saved application to equal an original response result, its submission to match an approved original subrecord, and its composite/variant ID to match. CRLs require complete original-result equality, letter type and file identity. Projections, aggregate-only responses, request receipts, mismatched identities and unsupported endpoints fail. Existing SHA-256 evidence checks remain.

Validated all four failed batch slices (61 rows) plus a more recent 14-row batch. Superseded/requeued **21 unfinished old-contract jobs**, preserved original data and failure evidence, enabled the source and replayed **five distinct jobs successfully**. Persisted reviewed-source date queues in local/runtime configuration and installation defaults. The source has zero consecutive failures; individual bad dates remain separately recorded and cannot stop this reviewed source.

**39 focused tests passed**, including approval and CRL identity, full response equality, duplicate-variant hashes, missing/projection/aggregate/wrong-host rejection, and metadata runtime regression checks. Installation and edited modules compiled.

## Live API and capture

Both authenticated API probes passed November 10 and saved their original responses:

- `/drug/drugsfda.json`: application `NDA017398`, approved submission `SUPPL:25`.
- `/transparency/crl.json`: `210274_2023_Orig1s000OtherActionLtrs.pdf`.

See `api-probes.json`. Probes use the existing secret resolution and shared request budgets; API key values are not logged. These probes validate service access, not completion of a collection scope.

The shared collector's November 9 run completed an **empty October 24** calendar window and advanced to **October 25**. The newest checked nonempty batch was ingested **October 31**, for an October 23 event window. That partial capture has a later complete/exhausted manifest retained in its task history; only that complete manifest was published here. Event dates, ingestion dates and publication times are distinct. Catch-up is still outstanding; no claim of current-day freshness or completed history is made.

A standalone status invocation found the controller's temporary universe symlinks unhydrated outside its managed S3 runtime. No universe files or shared runtime paths were replaced; capture state was checked from saved manifests and the retained managed-service journal instead. Its active managed capture schedule remains intact.

## Athena proof

Metadata aggregate query **`2864e5e7-cc4b-4155-8978-4a186907f778`** returned **75 observations / five distinct raw batch URIs / 75 raw-complete observations**. Latest nonempty ingestion was October 31, 11:01:04 UTC.

Metadata payload query **`736673d7-4ddf-4ad9-87fc-6cb94d9be0a8`** returned contract 2.0.3 rows with application IDs, approved submission status, original provider payload and provenance. The original aggregate query in the verification schedule works unchanged.

Published the complete October 23 window into the canonical regulatory tables: **14 regulatory records**. Staging verification query `886f7565-d8e6-41fd-8247-5021dd9a369b`; publication receipt in `fresh-publication.json`. Earlier sampled windows were already published and were not duplicated.

Curated payload readback **`27b2ba9f-3d56-480f-8f18-4fc31cce5be3`** returned application IDs `BLA761326`, `ANDA221194`, `ANDA202323`, approval status `AP` and complete JSON payloads.

To inspect full structured API evidence:

```sql
SELECT source_record_id, ingested_at, raw_s3_uri,
       json_extract(labelled_json, '$.payload.data') AS provider_data
FROM optima_metadata_engine.source_observations
WHERE source_key = 'fda_openfda'
ORDER BY ingested_at DESC
LIMIT 20;
```

To inspect the repaired curated window:

```sql
SELECT *
FROM optima_regulatory_pilot.research_records_windows
WHERE source = 'fda_openfda'
  AND window_id = 'fd1e6497b484d4080676550f779a8e59ef18082979ec39069adc3194d7de5813'
LIMIT 20;
```

These are current provider application/CRL records and dated approval/letter events. Action dates do not establish when data became public. Undated submissions remain explicitly undated. Linked documents, historical vintages, legal-company identity matches and complete source history remain separate checks.

## Runtime checks

All **15 collection workers** are active. Daily and historical collection controls permit work. Metadata worker timer is active; its successful eight-job cycle was observed. Metadata controller's latest result is success in its isolated slice. Shared daily collection, research-publication, historical-dispatch and metadata-controller timers are enabled/active. Owner pauses remain unchanged.

The worker had no failed units. Other sources still have validation holds. The controller's previously documented product-search failure (nonexistent `tracking` database) and code-backup failure are separate from openFDA; this repair does not claim those have been fixed.

## Evidence

`before.json`, `sample-record.json`, `failed-batch-validation.json`, `recent-batch.json`, `api-probes.json`, `metadata-deployment-result.json`, `migration.json`, `replay-result.json`, `publication.json`, `athena-verification.json`, `metadata_sample.json`, `fresh-publication.json`, `curated_payload.json`, `final-status.json`, `collection-controls.json`, `worker-health.json`, `controller-timers.txt`, `controller-health.txt`, `tests.log`.
