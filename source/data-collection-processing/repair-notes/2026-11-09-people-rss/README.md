# People RSS article capture and Athena repair — November 9, 2026

## Verified outcome

Marked `people_rss` reviewed after live capture, metadata validation, publication and Athena payload checks.

- Metadata query: **42 full-text/raw-complete observations linked to five raw batches**, including current-day repair. Query `5449657c-d653-4638-8f08-05f7bd5eed9a`.
- Curated payload: `optima_people_research.source_observations_windows` returned a repaired article with `capture_status=captured`, **2,939 text characters** and its extracted-content S3 reference. Query `2501b82d-f4ec-4ed6-9b3c-815f4c33018d`.
- One separately budgeted live Decodo diagnostic returned publisher HTML and **2,945 extracted characters**. This probe does not claim the direct URL was blocked.
- The independent repair worker completed a production run capturing **1,958-character BioSpace** and **3,018-character Energy Storage News** articles, with immutable manifests and metadata enqueueing.
- **40 focused regression tests passed.**

These are verified scopes and records, not complete historical coverage or assurance that every publisher URL is obtainable.

## Changes

`people_movements.py` preserves explicit RSS `content:encoded` / Atom full-content fields separately from descriptions. `people_rss_content.py` uses substantive explicit feed content first; otherwise it retrieves the publisher article and attempts Decodo after nonrestricted direct retrieval/extraction failures. Feed descriptions alone are not substituted for article text. Original bytes, extraction hashes, chunks and direct/rendered retrieval provenance are retained.

Explicit publisher access restrictions are not bypassed. Captcha/short/summary bodies cannot establish success. Decodo target/gateway errors and rate limits remain visible. New code reopens old unavailable cache entries for the new fallback; existing verified captures can be reused. Decodo requests are capped at 40/day for RSS, plus existing shared provider limits; publisher requests retain existing daily/run limits.

The daily collection task includes the new full-text version. Finite and maintenance backfill configuration has a fresh versioned registry identity so exhausted old attempts do not silently prevent new-code retries. Collector changes deployed to 149 historical workspace roots and local daily copies.

## Metadata and gaps

The old generic metadata contract had no publisher host configuration and could not verify feed/article content. New contract `2.0.3` requires a provider envelope and actual full-text evidence. `metadata_engine/people_rss.py` checks article identity, original stored HTML or explicit native feed body, SHA-256, extracted body and text checksum. URL-only, summary-only, blocked and mismatched text cannot pass as complete.

Metadata processing skips incomplete articles individually, persists their URLs/reasons in the job report and the durable `pipeline_failures` queue (`stage=rss_article_content`), and continues validating other articles. Successful corrected records resolve their article-specific gap entries. This avoids discarding an entire batch or stopping the whole source for one inaccessible page. Prior failure reports remain archived; 136 old-contract jobs were superseded/requeued using the new immutable contract.

The original query remains valid and now returns rows. The reviewed-source failure mode is deployed and retained in installer defaults. Remaining unprocessed snapshots and article-level gaps are recorded in `final-status.json`.

## Ongoing repair

`optima-rss-content-repair.timer` runs on `i-06241bd1c4e91c2fc`, every 120 seconds after completion. It processes at most two eligible article gaps, saves corrected native collection records and explicitly enqueues their metadata jobs. It skips fresh unavailable receipts during cooldown and retains independent budgets. Limits: **512 MiB memory, 25% CPU, eight-minute invocation timeout**; no shared controller capture lock is held.

The worker has only narrowly added GetObject/PutObject access to `operations/news/fulltext/people_rss/{content,decodo-budgets}/*`; no deletion rights were added. An initial import-path failure was fixed, then a complete successful production run was verified. Regular feed collection and research publication timers remain enabled. Existing committed-window discovery handles future curated publication; this repair published the representative corrected window immediately through canonical staging/count checks.

One tested article explicitly reported restricted access and remains unavailable; it was not published as full text. Other source/article gaps remain visible. No credentials or purchase are requested from the owner. Personnel movements, entity resolution and comprehensive workforce history remain separate, unverified assertions.

## Evidence

`tests.log`, collector/metadata deployment results, `failed-batch-validation.json`, `live-captures.json`, `decodo-live-probe.json`, `migration.json`, replay results, `athena-verification.json`, `curated-payload-verification.json`, `final-worker-result.json`, `review-policy-result.json`, `final-status.json`.
