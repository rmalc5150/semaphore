# Metadata engine — deployed operations

Deployed 30 October 2026. The processing queue is running; historical enumeration
and processing are ongoing. This is not a historical-completeness certificate.
Raw-content acceptance remains specific to the source contract and input.

## Placement and schedules

| Component | Host | Schedule | Limits |
|---|---|---|---|
| `optima-metadata-controller.timer` | t3 `i-070bab0b09f794629` | 120 seconds after the previous run ends | 256 MiB, 15% CPU, 240-second invocation |
| `optima-metadata-worker.timer` | m7i `i-06241bd1c4e91c2fc` | 60 seconds after the previous run ends | 512 MiB, 25% CPU, shared existing worker slice, 300-second invocation |

Worker code is installed at `/opt/constellation/metadata-engine-runtime` and
uses the existing `/opt/constellation/legacy-venv` environment. Controller code
and configuration are in `/home/ec2-user/data-collection-processing` and
`config/metadata-engine.json`.

The 158 catalog entries map to 156 source keys. Versioned runtime source
policies supplement the initial four pilot contracts. Their initial rules are
conservative and should be refined using the separate raw-source audit;
registration is not a claim that all 156 providers have complete raw data.

## Historical and daily intake

The controller incrementally enumerates existing shared raw batches, public
capture receipts, native committed collection jobs and daily raw records. Scan
positions are durable in RDS; passes repeat to discover newly added objects.
Large native manifests advance page by page; processing splits record batches
into groups of at most 32. No minimum historical date is imposed by this engine.

For shared daily collectors, `CollectionRun.finish()` can emit a metadata-intake
notice after the collection checkpoint commit succeeds. Controller service
drop-ins set `METADATA_ENGINE_NOTIFY=1`; existing daily workspace copies receive
the tested hook. A failed notice does not undo successful collection. The
controller consumes these notices at its next run with higher queue priority.

Collectors outside the shared storage interface are covered by bounded daily
discovery and the native collection commit/state checks. Discovery of a file
alone never establishes that collection committed it. Retained owner pauses
and NICE restrictions remain in force.

## Raw-data validation

The worker verifies collection commit evidence, source identity, byte counts,
raw SHA-256 and source-specific required artifacts. It rejects abstract-only,
index-only, title/date-only and unvalidated HTML/block-page evidence. Native
request receipts establish the actual first-party origin; a public record link
may legitimately use a different hostname. Explicit API field projections
(`printFields`, `fields`, `$select`, `select`) fail the full-raw requirement.

SEC filings use the tested original-submission retriever. Other sources must
already supply the raw artifacts demanded by their contracts. A missing
full-text/attachment validator is a visible gap, not permission to treat
metadata as original substantive content. Larger artifacts requiring a streaming
adapter remain operational retries rather than false source-content failures.

### EODHD: company reference and market data

EODHD has a separate `eodhd_provider_data` adapter and version **2.0.3**
contracts for `eodhd` and `eodhd_market`. The user explicitly designates these
as vendor company information and stock-market data. Primary documents,
issuer filings and unfiltered full fundamentals are not required for these
datasets. The complete archived response for the declared API scope is required.

- `company_profiles`: the complete returned **General** section, matched to
  the requested exchange-qualified symbol. All returned fields are retained;
  a missing optional LEI, CIK or description does not fail content validation.
- `listing_inventory`: the native exchange listing response, requested exchange
  and active/delisted scope, matched to the individual listing record.
- `market_records`: dated OHLCV/adjusted-close observations, dividends and splits;
  native fields and normalized values are cross-checked against archived bytes.
  Prices must have consistent OHLC bounds and splits a positive valid ratio.

Artifacts and labelled JSON explicitly carry `provider_role=third_party_data_vendor`,
their purpose and `completeness_scope=declared_provider_dataset`. Existing
`origin=first_party_source` means the bytes came directly from **EODHD**;
it does not identify EODHD as the company/issuer or label vendor claims as
original company evidence. Vendor descriptions/classifications remain provider
claims and identity candidates. They do not substitute for filings or papers.

Adjusted prices retain a current-provider-vintage warning. Neither a current
profile nor a downloaded historical price implies original historical
availability. A corroborated archived 404 profile response is an explicit
`provider_unavailable` outcome, with `profile_content_complete=false`; it does
not establish that the company does not exist. Malformed responses, wrong
symbols, missing prices, access errors and checksum failures still fail.

The old generic-rule stops are superseded when the corrected contracts pass
bounded replay. Their reports and previously sent notices remain historical
evidence. Only EODHD jobs move to the revised contract; other source stops and
the four-failure policy remain in force.

Provider, database and transport failures remain distinct. A failed/partial
collection does not become an empty successful window. Original bytes remain
immutable; labels and evidence references are derived outputs.

## Four-failure source stop and email

- A source's fourth consecutive **raw-content validation failure** stops its
  metadata processing (`engine_sources.state='raw_stopped'`).
- Each failed queued input is finalized once. Individual records within a
  failing batch do not each increment the counter. Retry of the same finalized
  job does not silently count as a new failure.
- A successful nonempty validation resets the consecutive counter. Empty
  results do not erase failures. Operational retries do not increment it.
- One transaction records the failed job, stopped source and an email-outbox
  entry. Other sources continue and the stopped source's backlog is retained.
- The t3 controller sends the stop notice through the existing confirmed SNS
  email subscription to `randall@optima-holdings.com`. Multiple stops can be
  grouped into one email. Failed delivery attempts remain pending for retry.
- Outbox delivery is serialized with a database named lock. A process crash
  between SNS acceptance and recording the message ID can cause a repeated
  notice; the system favors recoverable notification over silent loss.
- Collection schedules are separate: stopping metadata processing does not
  stop raw collection or automatically change provider credentials.

Repair the missing capture/contract evidence, then explicitly resume a source
on t3:

```bash
cd /home/ec2-user/data-collection-processing
.venv-athena/bin/python -B -m metadata_engine.control status
.venv-athena/bin/python -B -m metadata_engine.control resume --source arxiv
```

Resuming resets the counter and retries failed work. An unchanged deficient
historical input will still fail; resuming alone does not repair raw evidence.

## RDS, graph and analytical publication

Runtime state uses the existing scoped `metadata-engine/worker` secret and TLS
database connection. It does not use master credentials at runtime.

The additive migration `schemas/rds-metadata-runtime-v2.sql` adds queues,
failure counters, scan cursors, notification outbox, artifact/document links,
assertions, series identities/vintages and securities/listing-history tables
to the original entity/event schema. Evidence-bearing graph inserts are
idempotent. Direct identifiers yield provisional entities and explicit source
roles; no fuzzy-name merge or parent-stock attribution is performed. Source
record events are labelled `source_record_observed`; this is not an inferred
real-world-event classifier.

Validated labelled Parquet is written below:

```text
s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/metadata-engine/runtime-v2/
```

Each attempt has an immutable report and each artifact a checksum. The
controller registers a staging partition, verifies its exact row count through
Athena, then registers the public analytical partition and publication receipt.
Unverified worker output is not added to the published table.

```sql
SELECT source_key, count(*) AS labelled_observations
FROM optima_metadata_engine.source_observations
GROUP BY source_key;

SELECT source_key, state, consecutive_raw_failures, last_reason
FROM metadata_engine.engine_sources
WHERE state = 'raw_stopped';

SELECT source_key, sent_at, sns_message_id
FROM metadata_engine.engine_notifications
ORDER BY created_at DESC;
```

The first query runs in Athena; the latter two run in RDS MySQL. Athena stores
source observations, not deduplicated counts of inferred real-world events.
The graph remains in RDS; dedicated graph exports and specialist interpretation
are separate consumers of this evidence layer.

## Verification and initial production evidence

- 66 focused/local tests pass, including shared collection-storage regression
  tests, source/raw checks, record identity, daily commit ordering and native
  request-origin validation.
- Runtime regression checks also execute on m7i before installation.
- A rollback-only live RDS test proved four independent failures stop a source,
  exclude it from claiming, and create one durable notification. Synthetic
  rows were rolled back and no test email was sent.
- The real initial SEC batch produced 11 labelled records and passed exact
  Athena count verification; entity and filer-role evidence was inserted.
- Scheduled historical discovery and processing subsequently produced accepted
  and failed inputs. arXiv stopped after four missing-full-text failures.
- EODHD also stopped after four missing-verified-provider-artifact failures.
  These stops used the prior generic contract. SNS accepted the notices;
  they do not establish provider-side unavailability. After the user clarified
  EODHD's vendor-data purpose, bounded committed profile, inventory and price
  samples passed the new adapter on m7i. Version 2.0.3 superseded 438 old
  `eodhd` jobs and 410 old `eodhd_market` jobs and resumed both queues. Original
  failure reports and sent notices remain retained.
- The first bounded production jobs under 2.0.3 accepted 32 listing records
  (`a912fa1043eb114d5cdf39ad703af3e55ea69c285a582920cb95e0196154f99c`)
  and 21 market observations
  (`50efd00d459b6e8a0157e34b9dc99979d43cf3d901c977934bf3935cc83e9f5d`),
  committing their reports, RDS evidence and Parquet output successfully.
- A native NSF URL-mapping bug found during rollout was corrected. Affected
  batches were requeued; the current projection check separately rejects its
  restricted `printFields` captures where applicable.

Initial real SNS acceptance IDs:

```text
arxiv: ff95d8c0-c825-5381-be31-bb9e0d45dd15
eodhd: b9efc78b-9196-5f5f-a570-a4d55465a174
```

EODHD version 2.0.3 bounded replay receipt (three dataset samples, no new
provider requests; dividends/splits covered by local validation tests):

```text
s3://data-collection-059416028963-us-east-1-an/research-data/constellation-backfill/metadata-engine/runtime-v2/pilots/eodhd-provider-data/4ff848548efcc1686d5a5e4d943dd80ed1b5075668b1c0c27391dce419ff0c7e.json
```

Current queue counts change continuously. Use the status command above rather
than treating the initial observations here as live counts.
