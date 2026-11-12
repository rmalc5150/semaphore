# S64 company Bluesky monitoring

Deployed October 18, 2026. `bluesky_company_daily.py` snapshots the RDS company directory once per Madrid daily job and processes every company's account status. The timer resumes pending work every five minutes; completed jobs are not recaptured that day. Existing S64 sector search continues separately.

## Account setup and scope

Use existing RDS registry review workflows to enter verified `company_identifiers` rows with namespace `bluesky_did` (stable `did:plc:...` / `did:web:...`) and optionally `bluesky_handle` (`company.bsky.social` or a domain handle). The company must be verified, nonarchived and `collection_enabled=true`. Keep evidence establishing official account ownership on the registry identifier. This worker is read-only in RDS and does not admit entities or verify name matches automatically. Public profile search returns review candidates when a verified company lacks account identifiers. Reviewers must establish official ownership before enabling account monitoring. Current account ownership does not establish historical ownership.

The first live RDS snapshot had zero company rows; status explicitly records `no_companies_in_rds`, zero events and no created outputs. No fake company/account was added to production. Populate the directory through its existing workflow; subsequent daily snapshots pick up reviewed entries. Entries added after the day's snapshot are included in the following daily job.

## Outputs and event meaning

Sources `bluesky_company_accounts`, `bluesky_company_posts` and `bluesky_company_events` use dataset `specialist_inputs`. Account checks retain review candidates and exclusion reasons. Posts retain original records and API evidence. Event records contain `payload.data.event_id`, event version, source URI/CID, RDS company IDs, statement, outbound links, communication kind, timestamps and source evidence. Distinct event count and event-version count are reported separately.

The confirmed event is `company.social_post_published`. Content-based development candidates provide pending review routes, with matched spans and future/negated/uncertain wording retained. They do not independently establish a launch, approval, successful trial, financing or partnership. Product IDs remain empty until separately resolved and reviewed. Quotes/replies remain distinguishable; reposts are excluded. Main milestone correlation, material-claim promotion, specialist dispatch and model integration remain separate work documented in `ENTITY_DISCOVERY_ROLLOUT_PLAN.md#event-pipeline`.

Immutable source/event batches use the existing collection contract and specialist publication queue. RDS IDs are in payloads; top-level IDs remain empty because they belong to the separate static collection universe. Event occurrence uses a valid nonfuture source-created timestamp when available, while claimed creation, provider indexing and observation dates are separately retained. Historical availability/model eligibility remains unverified. Metrics changes do not create event versions; content CID changes do, under one stable URI-based event ID.

## Scheduling and recovery

- `optima-bluesky-companies.timer` / `.service`: enabled, persistent, checks/resumes every five minutes; one daily directory snapshot/job.
- `.venv-athena/bin/python -B bluesky_company_daily.py`: manual resume, guarded by a shared nonblocking lock.
- `config/bluesky-companies.json`: official public API base, seven-day initial lookback, two-day overlap, 20 company identity checks and eight feed pages per invocation, 100-page maximum per account/job.
- `bluesky-company-events.sqlite3`: daily directory, account cursors, reviewed handle bindings, successful watermarks, stable events/content revisions and output manifests.
- `reports/bluesky-companies-latest.json`: per-company/account status, coverage gaps, counts and publication status. S3 mirror: `operations/bluesky-companies/status.json`.

Resume interrupted account pages from frozen source responses. Commit both post evidence and event output before advancing cursor/version ledger. API errors retry three times with deferred retries. Page caps and missing/blocked/ambiguous accounts remain explicit; an incomplete feed does not advance the successful watermark. Deleted posts and unavailable history are not reconstructed or inferred from absence. Public author feeds are retrieved directly, so this job does not depend on sector-search completion. No automatic email/backfill was requested or added.

## SQL

```sql
SELECT source, record_id, event_at_json, payload_json
FROM optima_collected_data.observations
WHERE source IN ('bluesky_company_accounts','bluesky_company_posts','bluesky_company_events')
  AND dataset = 'specialist_inputs'
ORDER BY ingested_at DESC
LIMIT 20;
```

```sql
SELECT json_extract_scalar(payload_json, '$.company_id') AS company_id,
       json_extract_scalar(payload_json, '$.data.event_id') AS event_id,
       json_extract_scalar(payload_json, '$.data.event_type') AS event_type,
       json_extract_scalar(payload_json, '$.data.statement') AS statement,
       json_extract_scalar(payload_json, '$.data.version_reason') AS version_reason
FROM optima_collected_data.observations
WHERE source = 'bluesky_company_events'
  AND dataset = 'specialist_inputs'
ORDER BY ingested_at DESC
LIMIT 20;
```

Zero rows are expected while RDS has no eligible companies/accounts, or while committed output awaits asynchronous Athena publication. Refer to the status receipt to distinguish these cases. Count distinct event IDs for post publications; retain versions for revision analysis.

Primary API contracts: [author feeds](https://docs.bsky.app/docs/api/app-bsky-feed-get-author-feed), [handle resolution](https://github.com/bluesky-social/atproto/blob/main/lexicons/com/atproto/identity/resolveHandle.json). Account resolution alone is not company ownership evidence; the reviewed RDS binding is required.
