# Monthly patent research releases

The January 2015 global backfill is published and verified in Athena through a
separate, repeatable review and publication path. It uses the established
`patent_adjudication.Reviewer` policy:
specific CPC evidence can support a technology category; exact, unique names
can support links to registry-verified legal companies. Pending technology and
company matches remain queryable with reasons and their underlying evidence.
This is application of a reviewed policy, not individual expert adjudication of
every patent, proof of ownership, or historical model-feature eligibility.

Database: **`optima_patent_research`**, region **`us-east-1`**.
Workgroup: **`optima-patent-research`**, retaining the existing 100 MiB scan cap.
The original January 2025 pilot and its assignment/listing review tables remain
separate and unchanged.

New views:

| View | Contents |
|---|---|
| `patent_backfill_publications` | Publication/application/family IDs, authority, title, filing/priority/publication dates, CPCs, supported sector/company IDs, pending-review reasons, source references and JSON review evidence. |
| `patent_backfill_coverage` | One row per published month: exclusive source window, counts, universe and policy hashes, release ID and input manifest. |
| `patent_backfill_party_reviews` | Reported names and roles, supported/pending/ambiguous/unresolved identity status, company IDs where supported, reasons and evidence. |
| `patent_backfill_sector_reviews` | Separate supported and pending technology-category reviews with CPC or discovery evidence. |

Backing table `patent_backfill_records` contains publication rows and one
coverage row in the same Parquet dataset. The views separate them. Each monthly
Glue partition points to an immutable release location. Adding a month preserves
other months, and replacing an existing month with a different release requires
`--replace-window`. One partition contains both observations and coverage so
they switch together. Athena verification failures restore the prior partition
or remove a newly added one. Queries running during deployment may briefly see
the candidate partition before verification/rollback; this is not an isolated
database transaction. A local lock prevents concurrent deployment by this CLI.

Try these in the Athena query editor:

```sql
SELECT publication_month, publications,
       supported_technology_publications, supported_name_publications,
       unresolved_party_publications
FROM optima_patent_research.patent_backfill_coverage
ORDER BY publication_month;

SELECT publication_number, publication_date, filing_date,
       priority_date, family_id, title, supported_sector_ids
FROM optima_patent_research.patent_backfill_publications
WHERE publication_month = '2015-01'
  AND publication_authority = 'CN'
ORDER BY publication_number
LIMIT 25;

SELECT sector_id, category, review_status, count(*) AS reviews
FROM optima_patent_research.patent_backfill_sector_reviews
WHERE publication_month = '2015-01'
GROUP BY sector_id, category, review_status
ORDER BY sector_id, category, review_status;

SELECT reported_name, reason, count(*) AS reviews
FROM optima_patent_research.patent_backfill_party_reviews
WHERE publication_month = '2015-01'
  AND review_status <> 'registry_name_supported'
GROUP BY reported_name, reason
ORDER BY reviews DESC
LIMIT 25;
```

Filter `publication_month` for detailed research queries to prune partitions.
Company-sector membership and invention-sector classification are distinct.
The company links describe reported names, not current or historical ownership.
All new publication rows retain `current_ownership_status='not_established'`,
`available_at=NULL` and `point_in_time_eligible=false`. Older filing and priority
dates are retained as evidence even though the collection window is based on
publication dates starting in 2015.

Validation: 33 relevant offline tests passed. All four live verification queries
passed: unique publications and eligibility safeguards, coverage totals, supported
sector counts, and party/sector review views. The release directory contains
`athena-verification.json` with query IDs, counts and bytes scanned.

January 2015 publication, verified September 24, 2026 at 07:31 UTC:

- 37,738 publications across 66 authorities, including 7,050 CN publications.
- 25,551 publications have supported technology classifications.
- 958 have at least one registry-supported company-name link.
- 36,922 have at least one unresolved party or no reported party. This can
  overlap publications with a supported link when several parties are named.
- Supported sector memberships: biotech 8,846; semiconductors 12,630;
  energy storage 3,749; robotics 435. Multi-sector memberships overlap.
- 47,383 party review rows and 36,388 sector review rows.
- Parquet: 15,924,542 bytes, Snappy compressed, with round-trip validation.

Release:
`patent-backfill-athena-build/4a5442eba22748ad0dac0f9e1c21ba38309cc94d33de86caedeb0a162eca36e1`.
S3 prefix:
`research-data/curated/patent_backfill/releases/4a5442eba22748ad0dac0f9e1c21ba38309cc94d33de86caedeb0a162eca36e1/`.
The release includes the exact policy, universe and input manifest. Raw batches,
source evidence, committed manifests and their checksums are validated before
curation. Parquet and artifacts are read back after upload. Live query results
are stored in `athena-verification.json` and versioned S3 verification objects.

Publish a later completed monthly manifest using the same sequence:

```bash
.venv-athena/bin/python -B patent_backfill_athena.py prepare --manifest MANIFEST_KEY
.venv-athena/bin/python -B patent_backfill_athena.py publish --release-dir RELEASE_DIRECTORY
.venv-athena/bin/python -B patent_backfill_athena.py deploy --release-dir RELEASE_DIRECTORY
```

Prepare reads S3 but writes only the local immutable release; publish uploads
and verifies it; deploy attaches the month and checks Athena results. Partial,
uncommitted, corrupted, duplicate or out-of-window records cannot be published.
Each invocation accepts one monthly manifest, keeping memory and validation
bounded as the backfill grows. Repeated deployment of the same release is
supported. Schema/view-definition conflicts stop rather than modifying
unrelated catalog objects. SQLGlot compares parsed view definitions because
Athena reformats SQL while storing it; the dependency is pinned in
`requirements-athena.txt`.

## Automatic publication

`optima-patents-publication.timer` is enabled. Every ten minutes (plus up to
30 seconds of jitter), it starts `patent_backfill_publication.py`. It also runs
after boot. The service processes at most one completed month per invocation,
starting at the active patent backfill origin, **2021-01-01**, and catches up in order.
The September 24 cutover creates independent publication progress. The old
January–April 2015 partitions remain verified and queryable (164,690 publications);
the publisher only changes the month it is publishing.
It reads the same durable task checkpoints as the collector; it does not submit
BigQuery jobs or alter collection checkpoints. Partial months wait for completion.

The publisher applies the review policy, validates raw evidence, prepares Parquet,
uploads and reads it back, and verifies all four Athena queries. Only then does
it write an immutable monthly verification receipt and advance its separate S3
publication cursor. `verified_until_exclusive` is this contiguous publication
boundary; `collected_until_exclusive` is the independent raw collection boundary.
`pending_collected_months` exposes any publication backlog. The coverage view
shows attached months; during deployment, consult the S3 verification receipts
or publisher status to distinguish an attached candidate from a verified month.

Failures retain the pending month and retry on the next timer invocation.
Prepared releases are reused, and a crash after writing the verification receipt
can recover without repeating publication or double-counting records. Lost local
builds can be reconstructed from S3 evidence with the pinned configuration.
Normal query failures roll back the partition; abrupt termination can leave a
candidate attached until the same release is retried and verified. The publisher
never automatically replaces a different release in an existing monthly partition.

The review policy, curation version, Parquet runtime, schema and destination are
pinned in publication state. Changes stop publication for review rather than
silently revising existing months. Manual publication and the service share
`.patent-backfill-athena.lock`; raw collection remains independent. This is a
single-EC2 lock, not a distributed multi-host scheduler. EC2 must be running for
either timer to execute; both resume their persisted work after restart.

Configuration: `config/patent-backfill-publication.json`. Check operation with:

```bash
.venv-athena/bin/python -B patent_backfill_publication.py --status
systemctl list-timers optima-patents-publication.timer --no-pager
systemctl status optima-patents-publication.service --no-pager
journalctl -u optima-patents-publication.service -n 50 --no-pager
```

`waiting_for_collection` means the publisher has caught up with completed raw
months, not that the entire historical range is finished. `complete` means the
configured backfill range has been verified. `failed` includes the failed stage
and error; a later timer invocation retries it. A successful oneshot service
normally shows `inactive (dead)` between runs. The timer must show active.

S3 keys, under `research-data/operations/patents/global-backfill/streams/<stream>/`:

- `athena-publication/progress.json`: current stage, next month, counts and error.
- `athena-publication/months/YYYY-MM.json`: immutable verified release receipts.
- `athena-publication/failures/<id>.json`: immutable failure records.

The existing release `verifications/` objects contain the live query results.
Status records report the last verification; they do not continuously detect
manual catalog changes. The original January 2025 pilot remains separate.

Automation validation: 79 relevant tests passed, covering incomplete inputs,
ordered monthly processing, source-integrity failures, verification retries,
receipt/progress crash recovery, policy changes, and modified local releases.

Live activation on September 24, 2026: January and February 2015 passed all eight
Athena verification queries through the automated runner. Their durable receipts
cover **73,970 publications** (37,738 January; 36,232 February), with publication
progress at **2015-03-01 exclusive**. At activation, raw collection was complete
through April and those remaining months were queued for the active timer.
February release ID:
`dbdf48674112e79ffb14bdae9b4e05ec571cb4bc7634193799244459506c59c3`.
The timer was verified enabled and active; its first invocation correctly yielded
to the existing publisher lock. Later counts are available through `--status`.

## September 26 memory repair

Month preparation now consumes validated raw batches incrementally, writes
64-row Parquet groups, verifies every output value with a bounded streaming
round-trip, and uploads/checksums without reading the whole file into memory.
Source hashes, committed-manifest checks, observation/publication uniqueness,
review counts, and Athena verification remain enforced. A distinct encoding
identity prevents collisions with previous Parquet bytes. Existing verified
partitions and the semantic publication contract are retained.
