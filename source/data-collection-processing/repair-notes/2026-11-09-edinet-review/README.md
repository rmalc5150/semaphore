# EDINET owner review and live runtime check — November 9, 2026

Owner review is recorded as complete in `RAW_DATA_VERIFICATION_SCHEDULE.md`. EDINET's reviewed-source failure handling is now `queue_by_source_date` in local and worker runtime settings and the runtime installer. This retains individual raw failures without stopping the entire reviewed source. No validation requirement is waived.

## Repair and Athena verification

Found seven EDINET metadata retries with `larger_artifact_requires_streaming_adapter`. One original report ZIP was 1.8 MB, while its derived extraction JSON was 61,572,834 bytes. Generic validation attempted to load that derived JSON before reaching a valid 2.3 MB original PDF.

The EDINET evidence path now excludes derived extraction JSON from original-provider validation. Its references remain in the record payload. Original PDF/ZIP references still undergo normal provenance/checksum/content checks; an extraction-only record fails the original-document requirement. The 32 MB generic bound is unchanged.

All seven retries accepted after deployment. Published 18 accepted EDINET batches in four bounded calls (5, 5, 5, 3), each using staging Athena count verification before public partition registration. Publication receipts verify all seven repaired jobs.

Fresh Athena aggregate query `bccb8a46-4dde-4ccd-b387-3585319bc50e` returned:

- 138 observations;
- 138 distinct linked raw objects;
- 138 raw-complete observations;
- first ingestion October 22, latest ingestion November 1.

These are published sample/backlog records, not complete history or proof of daily freshness. EDINET still has thousands of queued input jobs. The original S3 objects and extracted content remain intact. No source credentials changed.

## Broader runtime check

Daily and historical collection controls both enabled. All 15 historical workers active (5 native, 6 legacy, 4 public). Metadata worker timer active; controller completes discovery and five-batch publication cycles. Fresh successful metadata jobs observed for SEC companyfacts, SEC filings, USGS, EODHD, NASA and Zenodo. Research publication completed verified SEC/regulatory/disclosure/people releases at 15:33 UTC.

No failed collection/metadata systemd services. The separate `ec2-code-backup.service` remains failed. Many controller services queue behind existing shared locks; activation alone is not proof of committed capture.

Remaining source states: 70 enabled, 78 raw-stopped, 5 owner-paused, 4 access-layer. Approximately 2,000 accepted metadata batches still await publication. Owner-paused sources remain paused. These source-specific holds do not mean the whole engine is stopped, and running infrastructure does not prove every pipeline correct.

Latest saved health report at 15:30 UTC has no inspection errors. Outstanding findings are collection prerequisites, market gaps (175 daily, 202 historical unresolved symbols, 52 reviewed exclusions), and patent PDF availability/source refresh. No blanket exclusions were added. Disclosure tables' latest published ingestion remains October 21, as separately checked earlier today.

## Evidence

- `tests.log`: focused EDINET evidence rejection/acceptance and metadata/HKEX/disclosure regressions.
- `review-policy-result.json`: deployed reviewed-source policy.
- `evidence-deployment-result.json`: atomic evidence module deployment and bounded replay result.
- `replay-jobs.json`, `replay-publication-status.json`: all seven repaired job commits/publication.
- `publication.json`, `athena-verification.json`: publication counts and live Athena aggregate.
- `runtime-status.json`, `worker-result.json`, `timers.txt`, `failed-services.txt`, service journals and `health-report.json`: bounded all-pipeline infrastructure checks and limitations.

No owner access action is required. Remaining raw-artifact repairs and catch-up are engineering work; owner content review remains separate per source.
