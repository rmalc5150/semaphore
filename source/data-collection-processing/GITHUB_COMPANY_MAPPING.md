# S46 repository/company mapping

Installed October 18, 2026. `github_company_mapping.py` reads the live RDS `tracking.companies`, `company_aliases` and `company_identifiers` in a consistent read-only transaction over verified TLS. It does not use the local company-universe file as the directory and does not write to RDS.

## Daily operation

`optima-github-company-mapping.timer` checks readiness every 15 minutes. The mapping service is ordered after `optima-specialist-daily.service` and independently validates each repository's S46 manifest. A daily mapping requires a complete, exhausted capture whose actual manifest finish date is today in Europe/Madrid. Partial, failed and stale captures remain waiting. Repositories proceed independently, so one incomplete history does not block other completed repositories.

A per-day/per-repository success ledger limits mapping and RDS rechecking to once per repository per Madrid day. Timer probes are not additional daily mapping passes. Failed metadata/directory requests can retry; they never mark success. A new directory entry after today's completed mapping is reconsidered on the next eligible day's capture. No capture means no fresh mapping or implied compatibility update. GitHub metadata calls share the existing public API hourly budget and preserve responses as source evidence.

Initialization used the latest available saved capture per repository, including partial history where necessary. These snapshots are explicitly marked `capture_mode=bootstrap`; they do not claim a completed capture today and do not consume the daily success slot. Subsequent runs require current-day completed captures. The existing Intel nightly history has partial capture receipts; this mapping job does not repair or certify that collection.

## Matching and review

The relationship is `repository_maintainer`, based on the current GitHub namespace, not legal IP ownership, employment, company endorsement, supported hardware or product compatibility. Match the repository's actual owner, not the release uploader or a build bot. Stable repository/owner IDs detect renames and namespace transfers.

- Names, reviewed aliases and matching owner/company website domains produce **candidates**, not verified relationships.
- A verified company plus an explicitly reviewed external identifier can produce a verified maintainer link. Supported `company_identifiers.namespace` values are `github_owner_id` (numeric GitHub owner ID), `github_organization` (owner login), `github_repository_id` (numeric repository ID), and `github_repository` (`owner/name`). These are application conventions in the existing free-form identifier table, not new schema fields. Owner/repository IDs are preferred over changeable names.
- Do not add these identifiers merely because a repository mentions a company's products. Enter them through the existing reviewed, evidence-bearing registry workflow; directory and identifier review states must both be verified. This worker does not seed identifiers or approve candidates.
- Conflicting verified company identifiers are downgraded for review. Rejected/archived companies and rejected aliases/identifiers are excluded. Directory changes are picked up on the next daily pass.
- On a repository owner-ID change, old repository-specific approvals cannot verify the new maintainer until re-reviewed; the identifier's evidence observation time must follow the observed transfer. A separately verified identifier for the new owner can establish its relationship. Retain historical snapshots.

At installation the RDS directory contained zero companies, aliases and identifiers. All five configured repositories were successfully checked and retained as `unmatched_directory_empty`. This is a successful unresolved outcome, not evidence that no real-world company maintains those repositories. The worker is ready to reconsider them as the directory is populated.

## Outputs and release joins

S3 prefix: `research-data/operations/github-company-mapping/`.

- `directories/<hash>.json`: directory evidence snapshot, without credentials.
- `snapshots/<day>/<mode>/<repo-id>-<hash>.json`: immutable mapping results with RDS directory hash, prior verified IDs, current owner, candidate/verified matches, capture lineage and GitHub source evidence.
- `latest/<repo-id>.json`: latest lookup pointer/content.
- `daily/<day>.json`: success ledger.
- `status.json`: readiness/errors. Local copy: `reports/github-company-mapping-latest.json`.

Athena table: `optima_collected_data.github_repository_company_mappings`. Select the newest check per stable repository ID before interpreting current mappings. The full S3 result retains match basis, role and transfer-review detail; the table exposes core matching/status/lineage fields. Originals in S46 remain unchanged.

Join releases using the repository in `payload.scope.url` (the capture's requested repository), not the author/uploader login. Each mapping keeps `requested_repository` and current full name, allowing a captured old path to be recognized after a rename. The mapping snapshot's date and capture manifest identify which source release inventory it checked. An old release associated with today's company mapping is a current identity association, not proof of its historical maintainer. No event-importance classifier, automatic product link or customer-adoption inference is introduced.

## Verification and operation

Tests cover current-day/partial capture gating, Madrid day boundaries, name/domain candidates, reviewed IDs, conflicting matches, empty/archived companies, transfers requiring re-review, and once-per-day idempotence. Run `.venv-athena/bin/python -m unittest test_github_company_mapping`.

Inspect `systemctl status optima-github-company-mapping.timer`, `journalctl -u optima-github-company-mapping.service` and the local status report. Manual invocation without flags obeys the daily gate. `--bootstrap` is for explicit initialization from saved captures and is not scheduled. RDS credentials come from the existing RDS-managed secret in memory; no passwords enter reports or mapping evidence.
