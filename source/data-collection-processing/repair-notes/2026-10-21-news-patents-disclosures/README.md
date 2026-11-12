# News, patents and disclosures repair — October 21, 2026

## Verified repairs

- **Finlight pagination:** when the final configured page is short, permit one additional empty-page completion probe. The probe still obeys the request budget; if it returns records, commit them and leave the window partial. Retained the boundary-page drift check.
- **Finlight live recovery:** refreshed the changed semiconductors/Chinese scope for October 16. All 253 records completed, and all eight target/language scopes for that daily window passed the window recheck. The typed Athena daily window contains 861 distinct articles and 1,000 observations across its eight target/language scopes. Subsequent daily dates remain backlog.
- **HKEX spreadsheets:** normalize unsupported column-width metadata and incorrect worksheet dimensions in an in-memory copy. Original document bytes remain intact. The second failing workbook now extracts 95,265 characters instead of only its first cell. Live replay completed all 727 filings for September 21, then completed seven selected documents and all four dependent event stages. Athena publication verified 727 filings, seven documents, two press-release candidates, two M&A candidates, four strategic-transaction candidates, and zero licensing-agreement candidates. These are unreviewed candidates within the configured universe, not confirmed events.
- **Dependency bookkeeping:** successful current-manifest recovery now clears its own stale reconciliation flag even when the run has used its one-window budget. Cached completion clears a flag only after current prerequisite manifests and the completed checkpoint match. Failed or changed prerequisites remain pending. All 14 operations tests passed with the checksum-verified production universe fixture.
- **Patent pagination:** resumed the interrupted hourly partition and published 300 additional patent records. A bounded page limit is unfinished work, not an authentication failure.
- **Petition decisions:** completed two historical date windows and advanced the cursor to September 15, 2021; published four decisions.
- **Patent failure diagnostics:** persist host, path, status and operation in the failed run's failure.json without API keys, response bodies or signed URL queries.

## Athena evidence

Actual successful count queries, followed by representative record_json queries:

| Batch | Records in published batch | Count query ID | Sample query ID |
|---|---:|---|---|
| Patent records | 300 | 0ca6e324-c4eb-4bd8-ad0f-ea75f02a5ecf | 1126792a-7247-49ca-9d53-402363fb37f6 |
| Petition decisions | 4 | e456023d-2b19-4022-8dff-fc28d7088e5e | 8461ab9e-512e-4837-950e-593393c2998d |
| Earlier HKEX replay batches | 500 | f31ea533-d3b1-44fd-839e-9476e810364c | 649e1edd-84a5-422a-b743-8179806fe61b |
| Earlier Finlight historical batch | 11 | 76ee25eb-0c34-452a-8eb7-224f8a30b00e | 9969af2b-e73f-4466-b784-f6c9d6fd672e |

These are committed batch counts, not unique-company counts or proof that entire source histories are complete. Stored observations can include successive captures. Samples contain underlying provider fields and source evidence, not just status rows. See athena-payload-checks.json and the corresponding *-sample.json files.

Typed-table count receipts and SELECT * samples are recorded in typed-athena-checks.json and typed-*.json. Run typed-checks.sql to inspect the specialist-facing columns, or verified-batches.sql to inspect the shared observation envelope. The SQL filters exact window/batch partitions before random sampling.

## Confirmed external limits

### USPTO office-action document access

The live request returned HTTP 403 for:
https://api.uspto.gov/api/v1/patent/applications/16545140/documents

Other patent requests succeeded. This establishes an endpoint/application-specific denial; it does not prove that the overall key is invalid or that the application has no documents. The January 1, 2021 office-action scope remains incomplete at 545 committed records.

Owner update, October 23: application 16545140 document retrieval is explicitly excepted at the owner's request. No support request is needed for this application. Index metadata remains collectable, with missing PDFs labelled `excluded_by_owner`; this does not establish that the underlying documents do not exist. See [exception verification](../2026-10-23-uspto-exception/README.md).

Daily office-action source-change recovery also retains its existing six-hour cooldown. The earlier failed window becomes eligible after 21:55:51 UTC on October 21. Eligibility does not guarantee successful recovery.

### Marketaux

Paused at the owner's request on October 21, 2026. Daily/historical API capture and content backfill are disabled; retained data remains available. No purchase or retry task is outstanding unless the owner requests resumption.

## Validation and operation

Focused news, prosecution and disclosure tests passed. Final disclosure regression run: 56 tests. Exact retained malformed spreadsheet bytes were also replayed through extraction.

Each repair has a durable log, explicit exit status and runtime checkpoint verification. A nonzero partial result remains visible even when orchestration succeeds. final-summary.json contains the latest sequence; the service restores previously active schedules in its finally block. Verify final-resume.json before assuming restoration succeeded. Reddit, Bluesky and GitHub remain intentionally paused.

## Final operational result

All 66 timers active before maintenance were verified active again; the four Reddit, Bluesky and GitHub-related timers remain inactive. See schedule-verification.json.

The five September 21 disclosure reconciliation flags were cleared after verifying each completed checkpoint and its exact current prerequisite manifests. See dependency-native-verification.log. Subsequent dates and other universe epochs still need normal catch-up; this repair does not claim their histories are complete.

The follow-up supervised reconciliation attempt timed out acquiring the busy supervisor lock before its child started. It did not run or lose data. The reconciliation was then completed through native S3 reads/CAS writes under the same collection lock, using a checksum-verified read-only universe snapshot; no shared runtime files were changed. The native verification log contains all 14 passing tests and each cleared flag.

Final user actions:
1. Review typed-checks.sql in Athena; confirm the columns, document text and candidate passages meet the specialist-layer requirements. Candidates may describe historical or proposed events.
2. No owner access task remains for application 16545140; the requested document exception applies.
3. No additional API purchase or key change is indicated by these repairs. Marketaux remains subject to the existing daily quota, and historical/daily catch-up continues on the restored schedules.
