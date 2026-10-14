# Shared output and run tracking — step 2

The shared persistence layer is implemented in `collection_storage.py`.
It provides local and S3 backends, JSONL batches, immutable run records,
resumable page checkpoints, and contiguous success watermarks. It makes no
network requests at import time. The new SEC `daily`/`historical` commands now
use this layer; see `SEC_COLLECTION.md`. Other collectors and the legacy SEC
commands still await migration. No AWS bucket, policy, schedule, or Athena
table is created by this implementation.

## Storage layout

Paths are relative to the configured local directory or S3 bucket/prefix:

```text
raw/
  source=<source>/dataset=<dataset>/ingestion_date=YYYY-MM-DD/
    run_id=run_<uuid>/page-00000000-part-00000-<sha256>.jsonl

manifests/
  configurations/
    universe/<configuration-hash>.json
    taxonomy/<configuration-hash>.json
  collection_runs/source=<source>/dataset=<dataset>/run_<uuid>/
    started.json
    pages/<sequence>-<receipt-hash>.json
    final.json

checkpoints/
  task_<task-hash>/head.json
  watermarks/stream_<stream-hash>/
    head.json
    history/<revision>-<receipt-hash>.json
```

Raw files contain one validated step-1 envelope per line. They are grouped by
the UTC date of `ingested_at`, even if a run crosses midnight. Source event
dates stay inside records. Configuration snapshots preserve the exact company
universe and taxonomy used for each task; subsequent edits cannot silently
change that task's meaning.

Started manifests, page receipts, final manifests, configuration snapshots,
and watermark history are immutable through this writer. Only `head.json`
pointers are mutable, and they require a matching revision token. This is
application-enforced immutability, not S3 Object Lock or a newly deployed bucket
policy. The local implementation uses an advisory process lock, atomic file
replacement, and fsync; use it on a local filesystem.

## Configuration

`config/collection-storage.example.json` defaults to local output. The actual
S3 bucket is intentionally unset. A caller can load settings with:

```python
from collection_storage import StorageSettings

settings = StorageSettings.load("config/collection-storage.example.json")
store = settings.store()
```

Precedence is defaults, JSON configuration, `COLLECTION_<FIELD>` environment
variables, then explicit `overrides` passed to `load()`. Relative local paths
resolve against the caller's working directory. For S3, explicitly select
`backend=s3` and supply a bucket. A bucket value alone does not switch backends.

| Setting | Meaning |
|---|---|
| `backend` | `local` or `s3` |
| `local_root` | Local output directory |
| `s3_bucket`, `s3_prefix` | Cloud destination; no existing project bucket is assumed |
| `region` | AWS region for the S3 client |
| `encryption` | `AES256` or `aws:kms` |
| `kms_key_id` | Optional KMS key, only with `aws:kms` |
| `expected_bucket_owner` | Optional account ID checked on S3 requests |
| `max_records_per_batch` | Default 1,000; splits larger provider pages into multiple files |
| `max_batch_bytes` | Default 8 MiB; hard limit per JSONL object and per record |

Credentials come from boto3's normal credential chain and never belong in
this file, task scopes, run manifests, or reason codes. Cursor values may be
opaque provider pagination tokens; treat checkpoint access as access to source
collection state. Provider credentials must not be embedded in cursors.

S3 writes use `If-None-Match: *` for new immutable objects and `If-Match` for
checkpoint updates. An existing identical object is an idempotent success;
different bytes are a conflict. An SDK without these parameters is rejected.
The boto3 minimum in `requirements.txt` is raised to the version used in the
offline integration tests. S3 client retries use standard mode with up to five
total attempts. The source collectors still need their own source-request retry
policies during migration.

The S3 execution role will need appropriate GetObject and PutObject access, and
permission to distinguish missing keys from forbidden objects (typically
scoped ListBucket), plus applicable KMS permissions when selected. Access-denied
and missing-bucket errors are never treated as a fresh empty checkpoint. No
policy changes are made here.

References: [AWS conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html)
and [boto3 PutObject](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html).

## Task identity and collection windows

`task_spec()` requires source, dataset, daily/historical mode, exact UTC window,
non-secret query scope, collector version, universe, and taxonomy. Windows are
`[start, end)`: start inclusive and end exclusive. An adapter must translate
this to its provider's calendar/timezone/query semantics.

The task hash includes all those fields and the configuration content hashes.
Changing a company selection, query, configuration, mode, or collector version
therefore creates a separate checkpoint. The scope must include every filter
that changes the source results; merely labeling two different queries with
the same scope is invalid adapter behavior. Record filtering and provider
completeness are adapter responsibilities, not inferred from record counts.

Historical jobs should use bounded windows rather than one enormous task.
Daily jobs should consult `read_watermark()`, use a configured overlap for late
records, and explicitly refresh previously completed overlap windows. The
shared layer supplies persistence; source-specific window planning arrives
with collector migration. Historical and daily streams have independent
watermarks so a backfill cannot move a daily job's checkpoint.

## Commit and resume protocol

1. `CollectionRun.start()` validates the universe and task, snapshots the
   configuration, creates an immutable started record, and conditionally claims
   the task checkpoint. Each attempt has a new run ID.
2. Fetch one bounded source page using `run.cursor`; normalize and validate
   records, using this attempt's run ID and their real ingestion timestamps.
3. `run.commit_page(records, next_cursor=...)` writes every JSONL part and an
   immutable page receipt, then conditionally advances the checkpoint. If any
   part or checkpoint write fails, the saved cursor does not advance.
4. Mark the final page `exhausted=True` and `next_cursor=None` only when the
   source's end-of-results condition is established. Record limits, timeouts,
   parse failures, or unhandled pagination must not imply exhaustion.
5. `finish()` writes an immutable final manifest before updating the task head.
   Its status is `complete`, `partial`, or `failed`.
6. Only a successfully committed complete manifest may advance the stream
   watermark. The explicit origin and contiguous coverage check prevent gaps.

`resume=True` takes over an interrupted, partial, or failed task from its last
committed cursor. Stop the previous worker first. It verifies committed batch
hashes and carries their references into the new attempt, preserving their
original run IDs. A stale worker is fenced by a conditional-write failure;
it must stop rather than silently retry under new ownership. Unfinished started
manifests remain as evidence of interrupted or superseded attempts.

`refresh=True` starts collection from the beginning, retaining earlier immutable
run records. It is useful for daily overlap, source revisions, expired cursors,
or failed completeness checks that require re-reading a window. Refresh and
resume are mutually exclusive. Starting a completed task without refresh raises
`AlreadyComplete`, whose message contains the final manifest key.

Replaying the exact same observations within a task drops duplicate observation
IDs. A fresh run's observations and changed source payloads are retained, as
required by step 1. This is not global logical-record deduplication: later
curation chooses the appropriate versions by record identity, payload hash,
availability, and ingestion time.

## Status and failure meanings

| Status | Meaning |
|---|---|
| `running` | Nonterminal task head; started manifest exists |
| `complete` | Explicit source exhaustion, no error reason, and expected count matches if supplied |
| `partial` | Incomplete coverage, such as a provider cap; a reason code is required |
| `failed` | Attempt failed; a reason code is required; prior committed pages remain recoverable |

Both partial and failed runs can have zero or nonzero committed records. A
successful empty result requires a committed terminal page with zero records;
an exception is never an empty success. `expected_records` refers to normalized
distinct observations for this task after duplicate suppression. Do not compare
an unfiltered provider total to a company-filtered output count without adapting
that check appropriately.

Final counts and page references describe cumulative task progress, including
inherited pages on resume. `resumed_from_run_id` identifies that inheritance.
The caller must report source errors explicitly, for example
`finish("partial", "provider_limit")` or `finish("failed", "source_unavailable")`.
Reason codes are plain identifiers; do not put raw exception bodies or URLs
containing credentials in them. If storage itself is unavailable, finalization
may also fail; the last durable checkpoint remains running and resumable rather
than inventing a terminal state.

If a response is lost after a successful write, the writer reads the object and
accepts success only when its bytes match the attempted write. If a process dies
after the final manifest but before the head update, the next start reconciles
that manifest before deciding whether to resume or report completion. In-process
finalization retries must use the same arguments and immutable manifest bytes.

Watermark updates are separate from finalization. Retry `advance_watermark()`
after a crash or conflict; it is idempotent and cannot regress. Complete windows
that arrive out of order retain their manifests, but their watermark update
must be retried after intervening gaps are filled. A refreshed task temporarily
has an incomplete head, but its `terminal_history` retains every previously
committed terminal manifest. Earlier complete coverage remains usable and its
watermark update can still be retried. A watermark describes successful range
coverage, not freshness of a later refresh attempt.

## How to consume output safely

**Only batches referenced by a committed checkpoint/final manifest count as
committed output.** A crash or competing worker may leave raw objects or page
receipts that were uploaded before their checkpoint commit. Do not interpret
an unrestricted recursive scan of the raw prefix as complete collected data.
To establish that a final manifest was committed, check its key in the task
head's `terminal_history`; the presence of `final.json` alone is insufficient.
That history survives refreshes, resumes, and later failures.
Later Athena curation must select committed manifests, deduplicate observation
references across resumed/overlapping runs, and explicitly choose how to use
partial results. No orphan cleanup or deletion runs automatically.

The implementation buffers at most one configured JSONL part while iterating
a provider page. The caller controls provider-page size. Checkpoint metadata
and the set of seen observation IDs grow with a task, so divide large backfills
into bounded windows. Resume reads prior committed batches to verify their
integrity and rebuild the ID set; it does not refetch those pages from the source.
Per-record validation is cached at the schema-validator level for bulk use.

## Local demonstration and tests

```bash
python3 -B collection_storage_demo.py --output-root /tmp/research-storage-demo
python3 -B -m unittest test_research_contract.py test_collection_storage.py
```

The demo writes two fictional records, ends its first attempt as partial,
resumes from page 2, completes, and advances a historical watermark. It uses
local output only and cannot select an S3 backend. A second invocation reports
the already-completed task. Never upload these fictional examples to production.

Tests exercise interrupted batch uploads, checkpoint failures, lost responses,
stale workers, finalization recovery, missing/corrupt batches, record/byte batch
limits, duplicate observations, exact task identity, empty success, failed and
partial runs, watermark gaps, and S3 conditional request parameters. AWS tests
use botocore Stubber and test-only credentials; no live AWS or source API is
contacted by these tests. Separate live SEC/S3 validation is documented in
`SEC_COLLECTION.md`.

## Next step

The SEC migration is implemented, tested offline, and validated with a bounded
live historical/daily S3 pilot. See
`SEC_COLLECTION.md` for operation, limitations, and legacy compatibility.
A bounded SEC-to-Athena pilot is now published and query-verified; see
`SEC_ATHENA_PILOT.md`. The first clinical/regulatory group now uses the shared
storage and has a live curated pilot; see `REGULATORY_COLLECTION.md` and
`COLLECTOR_MIGRATION.md` for completed sources, blockers and remaining stages.
