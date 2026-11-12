# Repaired-source Athena verification — 21 October 2026

## Outcome

All nonempty batches in the five specified repair manifests were already included in the live `optima_collected_data.committed_records` publication manifests. No additional publication or duplicate insertion was necessary. Actual Athena queries returned representative records for all five sources. This verifies publication and representative payload integrity; it does not certify complete historical coverage or fully normalized specialist inputs.

The reviewed CTIS historical manifest contains **zero records** and remains partial (`page_limit`). Existing CTIS records were queried separately; they do not establish that the repaired historical scope succeeded.

| Source | Records / files in reviewed repair checkpoint | Publication and payload check | Remaining limitation |
|---|---:|---|---|
| MHRA | 263 / 7 | All files published; last three files returned 129 rows as expected. Samples include company/product/indication regulatory snapshots. | Unknown historical designation dates remain null; company names are not verified internal company links. |
| CTIS | 0 / 0 | Existing trial records returned through the observations view, including trial IDs, sponsor information and dated country decisions. | Reviewed January 2021 scope remains unfinished; no repaired records to publish. Existing current trial observations are not historical public versions. |
| NMPA inventory | 23,460 / 1,179 | All checkpoint files published; last three files returned 58 rows as expected. Registration IDs, titles, status/listing fields and detail links inspected. Separate detailed trial and event records also returned. | Inventory is partial and is not equivalent to full detail coverage. Detail fields retain Chinese labels; entity linking and normalization remain separate work. |
| EDINET | 2 / 2 | Both repaired filing records returned: S100MK98 and S100MMO0. Filing metadata, capture/extraction status and document references inspected. All four S100MMO0 extraction artifacts parsed and passed SHA-256 checks. | Full extracted text/XBRL is in linked S3 artifacts, not inline Athena facts/text tables. Filer identity does not automatically identify the fund or subject company. |
| TED | 1,441 / 22 | All checkpoint files published; last three files returned 126 rows as expected. Notice 709615-2026 reconstructed from 89 Athena-returned chunks; checksum passed. Buyer, CPV, publication metadata, XML and enrichment inspected. | Counts include content chunks, not just notices. Chunked content must be reassembled before consumption. Extracted parties/values still require semantic and identity review. |

Counts above describe these resumable checkpoints, which can include earlier batches, not the entirety of each source or exclusively today's new captures.

## What you can verify now

1. Open Athena in `us-east-1`, workgroup `optima-collected-data`.
2. Run the examples in [SQL-checks.md](SQL-checks.md), one at a time.
3. Expand `record_json` and inspect `payload`. Check the source ID, dates, original fields and evidence references against the type of information you need.
4. For NMPA, inspect both inventory and detailed research records. For EDINET, distinguish metadata-only rows from captured-document rows. For TED, distinguish notice parents from content chunks.
5. Record any missing specialist field or incorrect entity match as a transformation/coverage issue; successful SQL alone does not certify readiness.

No credential or console repair is required from you for these publication checks. Engineering follow-up remains: CTIS historical scope progress; EDINET text/fact tables if SQL-only access to full content is required; normalized entity links and source-specific specialist transformations. Normal collection schedules were not changed. Reddit, Bluesky and GitHub remain paused.

## Evidence and method

- [Batch membership](batch-membership.json): exact repair manifests, checkpoint reasons and zero missing published files.
- [Primary query receipts](query-audit.json) and [bounded query receipts](bounded-query-audit.json).
- Individual `*-view-sample.json` and `*-repaired-sample.json` files retain the actual Athena query results.
- [EDINET artifact checks](edinet-artifact-checks.json): linked extraction files and verified hashes.
- [TED reconstruction check](ted-reassembly-check.json): complete chunk sequence, reconstructed byte count and verified hash.

The first EDINET exact-file count against the large committed table was stopped because planning remained slow (query `6a3a5b51-a696-4ec4-a26f-b28599d3de38`). It was replaced by successful queries against existing `batch_verification_records` partitions containing the same files. Publication membership was checked separately against the live committed table. No catalog or source data was changed by this audit.

### Successful sample query IDs

- MHRA observations: `13fcbeb1-8475-42bf-a7f9-bb7b230e06d0`.
  Repaired-file sample: `da22ae2a-2dbe-4ec6-93a1-ab222075f622`.
- CTIS observations: `3927520b-46ca-48c6-9012-b1427cbc347d`.
- NMPA observations: `b599e08e-98f6-4124-98ba-ffb1be2448f4`.
  Repaired-file sample: `b6aa139e-094d-422a-83b6-16ad5cd25e0b`.
- EDINET observations: `796ca160-30b0-4744-ad64-b6654561865d`.
  Repaired-file sample: `d9679c6d-acb2-4470-8c3f-3a202da5bf4d`.
- TED observations: `d57bf1eb-745b-4351-a134-cbf1af55701f`.
  Repaired-file sample: `a93ea1e3-0536-4be7-a292-8ca85a211c77`.
- NMPA detailed trial/events: `26576e51-523e-4b21-ab5f-9884d8187aa9`.
