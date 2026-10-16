# Event pipeline testing version

Started October 15, 2026. This is an isolated implementation of the recording experiment in [event-pipeline.md](event-pipeline.md). It reads a few saved records per available source/dataset, constructs inspectable candidates, and records what cannot yet be constructed. It is not a production event service.

The first completed run is documented in [results and findings](reports/event-pilot/README.md).

## What runs

[event_pilot.py](event_pilot.py) has four commands:

```bash
# Freeze saved S3 evidence locally. Requires the existing instance-role access.
# Use the managed data slice and heavy-job lock described below for execution.
.venv-athena/bin/python -B event_pilot.py capture --output reports/event-pilot/NEW-CAPTURE

# Reconstruct candidates offline from an existing capture; no AWS access.
.venv-athena/bin/python -B event_pilot.py build --capture reports/event-pilot/NEW-CAPTURE

# Copy review-template.jsonl, fill decisions, and record feedback locally.
.venv-athena/bin/python -B event_pilot.py feedback \
  --build reports/event-pilot/NEW-CAPTURE/builds/BUILD-ID \
  --decisions reports/event-pilot/my-decisions.jsonl

# Compare the effects of rule changes on frozen samples.
.venv-athena/bin/python -B event_pilot.py compare --before OLD-BUILD-PATH --after NEW-BUILD-PATH

# Offline behavioral checks.
.venv-athena/bin/python -B -m unittest test_event_pilot -v
```

The configuration is [config/event-pilot.v1.json](config/event-pilot.v1.json). It covers all 68 source-family IDs in the schedule inventory and maps actual collector names to those families. It defaults to **three distinct logical record/content versions per provider/dataset**, looking through at most three verified batches per route. Sampling prefers lexicographically recent ingestion/run/page keys, not random records or representative time periods. A family with several datasets can therefore have more than three samples.

Shared sources are discovered from a read-only snapshot of `committed-athena-index.sqlite3`. The sampler uses S3 GET requests to validate each selected batch against its terminal manifest and live checkpoint terminal history, and checks the byte hash, byte count, record count, source/dataset and selected observation hashes. It freezes those objects for offline inspection. Partial source windows may contribute committed sample records, with their incomplete status preserved; they do not count as complete historical coverage.

Reddit uses a separately labeled refreshable saved snapshot. Search uses retained, hash-checked DataForSEO capture receipts, not another paid request. Both retain their different provenance rather than pretending to be ordinary committed research envelopes. Provider routes without saved samples remain explicit gaps. Registering a planning source or a schedule does not invent source evidence.

No source provider API, Secrets Manager lookup, Athena query, S3 write, RDS write or production timer is used. Network activity is limited to retrieving retained evidence from S3. The run directory is local. A production registry, complete historical timelines, specialist scoring and model training are outside this test implementation.

## Resource limits

The capture requests at most 128 MiB of source/metadata content, with 8 MiB per shared source batch and 16 MiB per metadata object. Reddit permits one saved object up to 20 MiB within the same total budget. It caches exact objects so repeated reads do not consume additional download budget. Oversized/missing/uncommitted inputs become reported sample failures. There is no unrestricted raw-prefix enumeration or broad Athena scan.

The initial lock-waiting worker was replaced with a disk-backed light worker after inspecting the live data slice and the active heavy job’s 1.2 GB ceiling. Capture and builds completed as transient services in `optima-data.slice`, with `MemoryHigh=160 MiB`, `MemoryMax=192 MiB`, no swap and a bounded runtime. They do not take the heavy-job lock. The existing aggregate 2 GB slice ceiling still applies. These are one-off workers, not recurring timers; do not assume future concurrent headroom without checking it. The catalog snapshot and fetched object cache stay on disk rather than accumulating in Python memory. No collection checkpoint is modified.

## Inspectable outputs

Each capture directory contains frozen configuration, source inventory, taxonomy, pilot schema, source objects addressed by byte hash, `samples.jsonl`, and `capture.json` with route-level successes/errors. All evidence references resolve from this directory. `samples.partial.jsonl` is a best-effort interrupted-run aid, never the final build input.

`builds/BUILD-ID/` contains:

| File | Purpose |
|---|---|
| `REVIEW.md` | Source coverage, candidate summaries, supporting fields, and questions to resolve. Start here. |
| `events.jsonl` | Full candidate records with exact evidence/provenance, tentative classifications and proposed routes. |
| `outcomes.jsonl` | An outcome and reason for every unique sampled observation, including those that produce no event. |
| `coverage.json` | All 68 source families, actual sampled routes, remaining requirements and extraction rules. |
| `summary.json` | Counts of observations, candidates, event types and uncovered source families. |
| `events.sqlite3` | Local `events`, `evidence` and `outcomes` tables for joins and inspection. |
| `events.parquet`, `outcomes.parquet` | Locally verified Parquet exports for later isolated analytics experiments. |
| `queries.sql` | Local SQLite inspection queries and the boundary for later test Athena publication. |
| `review-template.jsonl` | Candidate/version IDs with empty reviewer, decision, reason and proposed changes. Copy before editing. |
| `implementation.py` | Exact extractor/build script used, retained so a later rule change does not erase the old implementation. |
| `manifest.json` | File hashes, build identity and capture receipt hash. |

Build identity includes frozen inputs, configuration, inventory, schema, taxonomy, and implementation bytes. Replaying unchanged inputs/code produces the same candidates and build path; existing artifacts cannot be overwritten with different JSON. Feedback is a separate immutable file. Pilot IDs use `test_evt_`/`test_ver_` prefixes and are not production UUIDs.

## How candidates are constructed

1. Apply source-specific milestone rules to structured fields: patent publication, official prosecution document, literature DOI/PMID, clinical registration disclosure, SDK release, recall, public notice or award disclosure where required fields are present.
2. For retained prose, suggest a small initial set of action types using explicit passages: leadership appointment/departure, launch, partnership, financing and acquisition. These are unreviewed pattern matches, not claims of reliable multilingual extraction or factual completeness.
3. Leave static directories, current ownership/profile snapshots, routine market/industrial series and search/social signals as context unless a specific supported milestone rule applies. A first snapshot cannot establish a change.
4. Return `needs_evidence` where no supported rule or sufficient original text exists. This is an extraction gap, not proof that the source contains no events.
5. Correlate only exact typed identities with declared namespaces. For example, the same DOI from two collectors can share a publication-disclosure candidate; different patent milestones and family members remain separate. Prose matching keys are source-scoped and never automatically fuzzy-merged.
6. Retain multiple evidence records, their availability and capture lineage. Independent reporting count stays unknown. Collector sector/search labels remain candidates; they are not verified sectors, subsectors or actual specialist-layer assignments.

Every event stays `candidate`/`pending`, with `point_in_time_eligible=false` and no model output. The pilot records a source event date separately from the candidate's occurrence; it does not assume that a current trial-update date is the registration date or a conference deposit date is the presentation date. The pilot schema is [schemas/event-pilot.schema.json](schemas/event-pilot.schema.json).

## Review loop

Review a few candidates alongside their original sampled records. For each, decide whether the action is specific and real, whether it should be one or several events, which sources refer to the same development, and which entities, occurrence dates, sectors/subsectors and actual specialist layers are supported. Also inspect `needs_evidence` outcomes to find developments the first rules missed.

Copy `review-template.jsonl` and submit only rows with a completed decision. Allowed decisions are `accept_candidate`, `reject`, `revise`, `merge_proposal`, and `needs_evidence`. Each requires the unchanged event/version IDs, a reviewer and a reason. Put desired field edits into `proposed_changes`. The feedback command validates and saves the response; it does not silently apply proposed edits, merge events or promote candidates into production. Implement the chosen rule changes explicitly, then replay the same frozen inputs to compare results.

Broad per-source sampling may contain no matching developments across providers. Test-fixture correlation checks are labeled synthetic; they are not evidence of real multi-source recall. After the broad review, select a small event-focused follow-up cohort to test actual PR/filing/news corroboration and scientific-publication links.

Before production, resolve extraction quality, actual entity roles and specialist IDs, source-version comparison, availability/corrections, source rights and any missing routes. Then implement the RDS outbox and immutable S3/Athena event publication described in the proposal. Local Parquet is not a deployed Athena table.
