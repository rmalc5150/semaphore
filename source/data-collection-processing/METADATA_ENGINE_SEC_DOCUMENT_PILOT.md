# SEC document retrieval pilot — 30 October 2026

Result: **accepted in the isolated pilot**. This extends the earlier negative
one-record pilot with actual original-document retrieval on m7i. Production
tables, collection schedules and the rest of the captured corpus were not
processed by this run. No database writes were made by the pilot.

## Scope and result

- Accession: `0000950170-24-067660`, CRISPR Therapeutics AG, form 8-K.
- Same source observation: `obs_866e949f1f5d34e553e5b3564fc5652e7cf9fb736144e4e9e737f4bd63452c57`.
- Existing logical ID retained: `rec_a09884ee48dbc487d39ccc418eae4371224969274de45382ea9f575cfbbd6007`.
- Source: <https://www.sec.gov/Archives/edgar/data/1674416/0000950170-24-067660.txt>.
- Retrieval: 30 October 2026 at 16:16 Madrid time (15:16 UTC); HTTP 200.
- Original byte length: **931,431**.
- SHA-256: `ca11cb9b18e68330810e97f392f72c3051eaaa1900117053e9cca7580a927e21`.
- Submission contains **11 embedded documents**, including `crsp-20240530.htm`
  (8-K), `crsp-ex3_1.htm` (EX-3.1), schema/XML files, the financial-report
  workbook and the XBRL ZIP. All remain inside the archived original bytes;
  document names, types and byte offsets are indexed in the receipt. Binary
  attachments were preserved, not decoded or analysed by this pilot.
- Raw evidence completeness: **complete for this SEC submission**.
- Historical information availability: **unknown**, preserved from the source
  observation. Neither the filing date nor Last-Modified was substituted for
  evidence of historical availability.

## Verification and storage

The pilot verified that the input run's final manifest appears in its checkpoint
terminal history. It checked the selected batch's byte count, SHA-256 and record
count against that manifest, then selected only the original first record.

The downloader restricted the HTTPS URL to the expected SEC issuer/accession,
sent the declared organization/contact User-Agent and made one bounded request.
It validated the accession, issuer CIK, form type, complete submission ending,
document blocks and presence of the primary 8-K. Limits: 16 MiB and a 45-second
socket timeout; HTTP denials and redirects fail without repeated requests.

Original bytes were conditionally written to a content-addressed S3 key using
AES256 encryption. Full byte and checksum read-back passed on m7i; an independent
controller download also passed checksum, length and submission validation.

Bucket: `data-collection-059416028963-us-east-1-an`.

Raw key:

```text
research-data/constellation-backfill/metadata-engine/source_documents/sec_edgar/ca11cb9b18e68330810e97f392f72c3051eaaa1900117053e9cca7580a927e21.txt
```

Pilot receipt, retrieval metadata and labelled observation:

```text
research-data/constellation-backfill/metadata-engine/pilots/sec-document/409552c1-a2c4-4541-bc12-c07f75b4f2cf/report.json
research-data/constellation-backfill/metadata-engine/pilots/sec-document/409552c1-a2c4-4541-bc12-c07f75b4f2cf/retrieval.json
research-data/constellation-backfill/metadata-engine/pilots/sec-document/409552c1-a2c4-4541-bc12-c07f75b4f2cf/labelled.json
```

The provider-record artifact is explicitly described as an existing collected
envelope derived from the SEC index. Original filing evidence comes from the
separately downloaded complete SEC submission.

## Implementation and tests

- `metadata_engine/sec_documents.py`: bounded SEC retrieval, submission
  validation, conditional storage and independent S3 read-back.
- `metadata_engine_sec_document_pilot.py`: fixed one-record scope, committed
  input checks and immutable isolated outcome receipts.
- `metadata_engine_deploy_pilot.py`: packages code on t3, deploys a distinct
  release on m7i, checks the package SHA-256, runs tests and the pilot.
- `metadata_engine/labelling.py`: retains research-contract record IDs, links
  the original observation ID and excludes the labelling clock from replay
  identity.
- `test_metadata_sec_documents.py` and `test_metadata_engine.py`: **15 tests
  passed locally and on m7i**. Tests include wrong accession/CIK/form, bad
  URLs, block pages, truncated HTTP and SGML, missing primary documents,
  corrupt S3 read-back and replay identity.

m7i instance: `i-06241bd1c4e91c2fc`.

Installed pilot release:

```text
/opt/constellation/metadata-engine-releases/444959e86849409555a1ec2635a4a0a4ca9cfef307b041e4a0e328d8a139510e
```

SSM command: `d0b57f7c-479a-493c-9362-17dcc9a7adb6` (`Success`).

## Remaining boundary

This proves one SEC filing can meet its original-document requirement. It does
not establish completeness for every SEC form or other source, nor certify the
existing corpus. Larger filings above the pilot limit remain explicit failures.
Recurring queue integration, resource admission, document reuse, RDS artifact
registration and Athena publication remain subsequent implementation stages.

SEC describes index text URLs as the complete disseminated filing content in
[Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data).
