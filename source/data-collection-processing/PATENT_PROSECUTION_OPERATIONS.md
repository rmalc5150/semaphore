# US examination and petition collection operations

Implemented October 14, 2026. The historical backfill has begun at January 1,
2021. Its pinned exclusive historical cutoff is October 14, 2026. This adds
evidence to existing patent collection; it does not reset application, assignment
or global publication backfills.

## Collector and storage

`patent_prosecution.py` implements `uspto_odp/patent_office_actions` and
`uspto_odp/patent_petition_decisions`. The existing `patent_collection.py` CLI
also exposes `office-actions` and `petition-decisions`. Payloads are validated
against `schemas/patent-prosecution-payload.schema.json` during storage and
curation. Original search JSON, metadata and PDFs are content-addressed in S3;
failed downloads have durable task receipts and leave source pages partial.

Office Actions use the live `/api/v1/patent/oa/oa_actions/v1/records` endpoint,
form-encoded Lucene queries and `submissionDate` historical windows. The index
includes allowance notices and other document types as well as rejections;
retain the document code instead of assuming every result is a rejection.
`obsoleteDocumentIdentifier` is matched to the official application's document
listing before retrieving a PDF.

Petitions use `/api/v1/petition/decisions/search`, `decisionDate` historical
windows, provider decision IDs and an explicit
`finalPetitionDecisionIndicator:true` filter. The unfiltered search includes
non-final decisions, which are outside this dataset's current contract.

Both sources returned January 2021 documents in live validation, including
Office Action documents for applications filed before 2021. The exact provider
"No matching records found" 404 is retained as evidence and treated as an empty
search; other 404s remain failures. PDF redirects are allowed only to the
verified `data-documents.uspto.gov` host and omit the API key. Redirect URLs
are not retained; evidence links use the original official download URL.

## Historical and ongoing work

`patent_prosecution_operations.py` maintains independent per-dataset historical,
incremental and reconciliation progress. Its configuration is
`config/patent-prosecution-operations.json`. Historical tasks use daily windows,
which include in-range documents for older applications. Incremental tasks use
`lastModifiedTimestamp` for actions and `lastModifiedDateTime` for petitions,
restricted to action/decision history from the current shared January 2021 start.
The incremental origin is the pinned historical cutoff; only completed provider
calendar days are queried. Source timestamps without zones are not promoted to
known public-availability instants.

The enabled `optima-patents-prosecution.timer` resumes work hourly. The service
uses `optima-data.slice`, a 128 MiB memory ceiling, zero swap and a 45-minute
timeout. Each window allows five records per page, ten pages, 180 requests and
64 MiB of PDF traffic. Each invocation attempts up to two windows per dataset
per stream. Quota exhaustion leaves partial work. All application and prosecution
requests share the host-wide gate in `uspto_rate_limit.py`, initially reserving
API request starts at least two seconds apart. Measure throughput and source
limits before increasing these initial bounds; no completion-date estimate is
established.

Recent update windows are reconciled over seven days. A separate rotating older
history sweep checks for delayed additions and corrections outside recent update
windows. Reconciliation has its own task scope so it cannot reset the historical
checkpoint. A partial sweep resumes on later scheduled sweep attempts. Source
mutation triggers a recorded restart cooldown of six hours. The Office Action
API ignored an attempted sort parameter in live validation: the collector checks
totals, repeated identities and boundary-page hashes at resume/completion instead.
These checks do not establish snapshot isolation; coverage remains provider-index
coverage, not complete US prosecution history.

```bash
.venv-athena/bin/python -B patent_prosecution_operations.py status
.venv-athena/bin/python -B patent_prosecution_operations.py historical
.venv-athena/bin/python -B patent_prosecution_operations.py daily
systemctl status optima-patents-prosecution.timer optima-patents-prosecution.service
journalctl -u optima-patents-prosecution.service --no-pager
```

The runner lock prevents concurrent scheduled/manual workers. Do not launch a
second direct collector for the same task. Do not refresh a running task. Partial
exit status 2 is an expected bounded-work outcome and is accepted by the service.
Operational receipts are under
`operations/patents/prosecution/<stream-id>/`; original observations remain under
`raw/source=uspto_odp/dataset=<dataset>/` and shared collection manifests.

## Publication and consumers

The existing `research_publication.py` workflow recognizes both datasets, using
`patent_prosecution_athena.py` for typed observations. Owners/configurations are
`patent_office_actions` / `config/patent-office-actions-athena.json` and
`patent_petition_decisions` / `config/patent-petition-decisions-athena.json`.
The respective databases are `optima_patent_office_actions` and
`optima_patent_petitions`. Only complete committed windows are eligible for
publication, with source/PDF checksum verification, Parquet round-trip validation
and the existing bounded Athena verification process. The enabled
`optima-patents-prosecution-publication.timer` runs the dataset-specific publisher
every 15 minutes with a 128 MiB memory ceiling and 15-minute timeout. It shares
the existing publication lock; an active publisher causes a later retry, not
concurrent catalog writes. Dataset-specific discovery avoids scanning unrelated
historical checkpoints.

Observation columns include application number, official document ID where
singular, document type, action date, source update time, first observation,
download status, document metadata, reported parties, structured source fields
and provider text. The full envelope and lineage are retained. Petition records
may contain several documents; use the retained document identities rather than
assuming one decision equals one PDF.

Historical, incremental and reconciliation releases can observe the same source
document. These are observations, not independent corroborating events. Join by
normalized US application and official-document identity, then select the
appropriate captured version for the consumer's cutoff. Do not count repeated
observations as additional patents or examination milestones. Availability is
unknown and `point_in_time_eligible` remains false.

Both bottom-up discovery routes and the event recording adapter remain future
implementation work in their respective plans. They can consume this evidence
without downloading it again; company/product links and outcomes still require
review.

## Execution evidence

The bounded historical pilot committed five Office Action observations and three
final Petition Decisions with original PDFs. Petition query windows through
January 5, 2021 completed; Office Actions remained partial within January 1 at
the pilot page limit. The regular service resumes those checkpoints.

[Pilot verification](reports/uspto-prosecution-2026-10-14/pilot-verification.json)
records read-back verification of the observations and 16 referenced source
artifacts. This is evidence that backfill began, not full historical coverage.
The first regular cycle subsequently reached 55 Office Action observations and
four final Petition Decisions. Five completed pilot petition windows were
published and verified in Athena, including three nonempty decision observations.
Office Action publication remains pending completed source windows. The current
status command and systemd journal supersede these initial counts.

127 related collector, storage, contract and publication tests passed during
rollout; the systemd unit definitions also passed verification. Tests exercise
interrupted downloads, successful-PDF reuse, source changes, corrections,
final-only filtering, redirect credential stripping, typed joins and corrupt
evidence rejection.
