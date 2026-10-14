# Explained market coverage gaps

A market window has three distinct outcomes: collected, unresolved, or excluded
with a documented explanation. Excluded windows are omitted from retries and
unresolved-gap alerts, but remain visible in coverage reports. They never create
prices, successful collection manifests, publication queue entries, or verified
collection timestamps.

## Scope and evidence

Every decision names the market stream, EODHD symbol, exact candidate listing IDs,
a finite interval (start inclusive, end exclusive), reason, explanation, reviewer,
review time, and saved evidence keys with SHA-256 checksums and source URLs.
The registry lives beside the existing market stream in S3; changing it does not
create a new collection stream or reset existing progress.

Supported reasons:

- `pre_ipo`: the entire interval ends on or before the documented first trading/IPO
  boundary. Check that the date applies to this listing, and that returned prices
  do not contradict it. Company IPO dates may differ from secondary listings.
- `post_delisting`: the entire interval starts on or after the documented boundary
  of no further trading. Use the first non-trading date, not an ambiguous notice date.
- `documented_unavailable`: saved evidence explains why prices are unavailable
  for the interval. Identify whether this is a provider limitation or an official
  exchange closure. A provider limitation alone does not establish that trading
  sessions did not occur or that another provider lacks the data.

An empty API response, the first returned price, an undated delisting flag, or a
transient authentication/network failure is insufficient by itself. Both lifecycle
reasons require `boundary_date`. Exclusions apply only when they contain the full
requested window; a year overlapping an IPO remains collectible. Excluding a
window skips this combined market-price/action job for that interval and explicitly
makes no claim that prices or corporate actions were collected.

## Review, apply, and revoke

Commands use the normal S3 settings and the existing market collection lock. If a
collector currently holds that lock, retry after it finishes. None of these commands
contacts a market provider or sends notifications.

```bash
# Read the registry and a current view of actionable/excluded coverage.
.venv-athena/bin/python -B market_coverage_exclusions.py report \
  --output reports/market-coverage-review.json

# Apply reviewed decisions and reconcile current state immediately.
.venv-athena/bin/python -B market_coverage_exclusions.py apply decisions.json

# Undo one decision and restore its windows to the retry queue.
.venv-athena/bin/python -B market_coverage_exclusions.py revoke EXCLUSION_ID \
  --reviewer 'Reviewer name' --explanation 'Corrected listing evidence'

# Reconcile state after an interrupted apply/revoke, without provider requests.
.venv-athena/bin/python -B market_coverage_exclusions.py reconcile
```

`decisions.json` is a JSON array. The applied, evidence-verified examples are in
[reports/market-pre-ipo-exclusions-2026-09-27.json](reports/market-pre-ipo-exclusions-2026-09-27.json).
The October 1–7 Shanghai/Shenzhen closure reviews are in
[reports/market-holiday-exclusions-2026-10-05.json](reports/market-holiday-exclusions-2026-10-05.json).
All fields shown there are required except `boundary_date` for
`documented_unavailable`. Evidence objects may also retain their retrieval time.
Evidence must already exist in the configured research-data store; the CLI verifies
its bytes before applying a decision. The reviewer is responsible for the evidence's
meaning and its relationship to the exact listing. A checksum verifies content,
not the truth of a claim.

An unresolved closed daily month is retained in `gaps` while `scan_next_date`
allows collection of subsequent months. `next_date` remains the earliest unresolved
gap. Once the forward scan catches up, retries rotate through saved gaps; only
collected or reviewed excluded windows leave that ledger. Open months continue
to be refreshed as they fill in.

Decisions are content-addressed. Reapplying the same active decision is idempotent.
Changes and revocations create immutable audit receipts. A revoked decision cannot
silently reactivate; a new reviewed decision is required. Removing/revoking coverage
restores gaps on the next reconciliation; monitoring also computes the current
registry view without waiting for a collector run. Original provider manifests
remain untouched, including evidence of failed empty-price attempts.

## Understanding the flags

`market_operations.py --status` now includes a `coverage_review` section. Each lane
reports actionable symbols/gaps separately from `excluded_windows`, with decision
IDs, explanations, evidence, and original gap manifests. `next_date` advances over
reviewed exclusions as well as collected windows; inspect these separate outcomes
when assessing data completeness.

Health reports expose excluded-window counts. Fresh registry-aware checkpoints
supersede stale aggregate journal counts. A reviewed exclusion can resolve only the
two market coverage alerts, and only when no corresponding actionable gaps remain.
It cannot resolve authentication, service failure, integrity, or unrelated-source
alerts. Exclusions are never labeled as verified collection progress.

The initial review excludes eight historical windows (2021–2024) across AAPG.US and
AARD.US. AAPGV.US remains for review because its reported IPO date conflicts with a
returned price date. See the [review report](reports/market-coverage-review-2026-09-27.md).
