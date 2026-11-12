# S68 institution identities and NIH grant lifecycle enrichment

Implemented 2026-10-18 in `grant_enrichment.py` and `grant_pipeline.py`. Original NIH (`S36`, `nih_reporter`) and ROR (`S68`, `ror_institutions`) observations remain unchanged. ROR is an identity registry, not a funding ledger.

## Daily and backfill execution

`optima-grant-daily.timer` checks every five minutes but creates one job per Madrid calendar day, only after a completed/exhausted NIH daily capture. It resumes unfinished work before starting the next day. `optima-grant-backfill.timer` resumes the separately pinned backfill. Both share a nonblocking lock, bounded work per invocation, three attempts with deferred retries, and resource-limited systemd services. HTTP, shape, identity, pagination and count errors become explicit gaps after retries.

Backfill `grant-backfill-2026-10-18` pins 42 committed input batches: 1,804 NIH observations and 55 ROR observations. Checksums and input counts are validated. Semantic project versions are deduplicated while every originating observation and batch reference is retained. Original ROR candidates are also republished with their original evidence and review status. The ledger is `grant-enrichment.sqlite3`; configuration and inventory are `config/grant-enrichment.json` and `reports/grant-backfill-2026-10-18/input-batches.json`.

For each known core project, retrieve all available NIH application years explicitly within fiscal years 1985 through next fiscal year, independent of the original topic/date filter. Exact returned core-project identity, pagination totals, duplicate identities and counts are checked. This extends known projects; it is not a search for every award received by each institution. Current API records do not reconstruct historical database vintages. Publications are retrieved through NIH's official core-project association endpoint. Clinical trial IDs explicitly present in project text are retained as candidates requiring registry validation; no claim of exhaustive trial or patent linkage.

Original response bodies are checksum-addressed under `source_documents/grant_original_evidence/`; successful complete lookup responses are cached per job. ROR searches retain every returned candidate. Matching requires a unique active exact official name/alias plus corroborating country and city without conflicting US state. Name alone, competing candidates, missing corroboration, medical-center versus university differences and parent/related relationships remain unresolved. Current registry relationships never establish past affiliation or automatic grant rollups.

## Outputs

All six sources use `optima_collected_data.observations`, dataset `specialist_inputs`, with `payload_json.enrichment_version = grant-lifecycle-evidence-v1` and `payload_json.job_id`.

| Source | Content |
|---|---|
| `grant_institutions` | Names/aliases, ROR and external IDs, websites/domains, locations, status, parent/related identities, registry administration metadata and original evidence. Includes saved original candidates. |
| `grant_institution_links` | Application/core-project IDs, recipient as reported including IPF/UEI/DUNS, candidate assessments, selected ROR if corroborated, all parent observation/batch links, review status and evidence. |
| `nih_grant_facts` | Full project abstract/title/public-health relevance, fiscal year, application/full/core numbers, award type, funding agency/ICs, activity/mechanism/opportunity, source-reported costs, budget/project periods, notice date, investigators/profile IDs, explicit NCT IDs. |
| `nih_grant_lifecycles` | Available application sequence per core project: new application, competing renewal, supplement, continuation, extension, successor or institution/awarding-IC transfer, strictly from documented NIH codes. No lifetime funding sum. |
| `nih_grant_publications` | Official core-project–application–PMID associations; empty results are explicit. Does not establish exclusive funding, research success or product efficacy. |
| `grant_entity_connections` | Read-only RDS company, person and product candidates/identifier bindings, roles and source field paths. No inferred employment, product ownership or allocation of funding. |

Application/fiscal-year/subproject identity and semantic source-version IDs are kept separately. Earlier versions remain immutable; downstream users must select one reviewed/latest version before aggregating. Award amounts are source-reported application/fiscal-year funding, not payments or company revenue. Do not sum parent awards with subprojects, annual records with lifetime totals, duplicate topic captures or source revisions. Planned project/budget end dates and `is_active=false` do not prove completion, termination or cancellation. `award_notice_date` is the grant notice issue date; neither project start nor ingestion date substitutes for it. Top-level `event_at` remains null on evidence outputs; lifecycle date and date basis are explicit within facts.

## RDS matching

A consistent read-only TLS directory snapshot is retained per job. Confirm company bindings only through reviewed exact `ror`, `uei` or `nih_org_ipf` identifiers; organization-name matches remain review candidates. Confirm investigator bindings only through reviewed `nih_pi_profile` person identifiers; names remain candidates. Product names/verified aliases mentioned in title, abstract or public-health text produce review candidates with field paths, not confirmed product funding. A recipient-company match does not attribute its grant to all products. ROR parent/related institutions are distinct entities. Do not create or overwrite RDS registry entities from these candidates.

The current RDS company, people and product directories are empty. Evidence extraction and lineage still operate; mappings remain `unmatched_directory_empty` until reviewed registry entries exist. Subsequent daily jobs re-read RDS. Additional funding authorities require separate authoritative adapters rather than treating ROR as an award source.

## Completion notification and operation

Email goes to `randall@optima-holdings.com` through the existing confirmed SNS topic, only after all lookup tasks are terminal, every grant version has facts, every output batch has a successful committed-Athena verification receipt, and exact per-source/job/version Athena counts agree. Gaps are disclosed, with full completion receipts under `operations/grant-enrichment/<job>/`. Timers keep waiting while publication catches up. Status is in `reports/grant-backfill-latest.json` and corresponding S3 `status.json`. No completion email is sent at launch.

Run manually with `.venv-athena/bin/python -B grant_pipeline.py --mode backfill` or `--mode daily`. Do not change the pinned inventory mid-job. See `ENTITY_DISCOVERY_ROLLOUT_PLAN.md#event-pipeline` for required production event integration; this worker produces evidence and lifecycle candidates, not production events.

## Primary definitions and validation

- [NIH RePORTER API](https://api.reporter.nih.gov/) and [project data dictionary](https://api.reporter.nih.gov/documents/Data%20Elements%20for%20RePORTER%20Project%20API_V2.pdf): application types, notice dates, budget periods, identifiers and fiscal-year funding.
- [ROR matching documentation](https://ror.readme.io/docs/matching): institution identity resolution; search results require matching assessment.

Focused tests cover institution mismatch/ambiguity/conflicts, lifecycle date semantics, application-type distinctions, source-version and lineage retention, subproject/double-counting protection, identifier versus name matching, explicit trial IDs, family response identity and premature-email gates. Live NIH retrieval was checked against a saved core project with six annual records and an official publication association.
