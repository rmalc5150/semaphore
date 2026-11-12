# S59 BLS labor context and evidence joins

Updated October 18, 2026. Source remains `bls_wages` / `specialist_inputs`.

`bls_enrichment.py` adds definitions, normalized reference month/decimal values,
footnotes, preliminary flags, monthly/yearly changes and all-employee manufacturing
employment, weekly hours and overtime. Daily collection checks 2021 through the
current year for revisions. Durable observed snapshots preserve prior versions
and distinguish first observation, repeated fetch, numeric and quality changes.

`bls_evidence_joins.py` adds three joins:

1. **Release evidence.** Official BLS archive links, embargo timestamps and original
   manufacturing AHE values from table B-3 are separately retained for 68 months.
   The official archive explicitly records no October 2025 Employment Situation
   release. Pinned browser extracts are in `config/bls-release-bootstrap.json` and
   `config/bls-release-vintages.json`, retaining source URL, retrieval method,
   original table/header excerpt and timestamp evidence. Direct automated BLS
   archive downloads currently receive access denials; the daily collector retries
   the official index and uses this labeled evidence fallback. Missing new archive
   entries or unparsed tables remain pending. A first-release timestamp belongs to
   its original archive value, never to a later revised API value. Saved API
   publication timing and record-level point-in-time eligibility remain unknown.
2. **Quarterly compensation.** BLS API series CIU2013000000000I (ECI compensation),
   CIU2023000000000I (ECI wages), CMU2013000000000D (ECEC compensation),
   CMU2023000000000D (ECEC wages), CMU2033000000000D (ECEC benefits) are collected
   together with evidence. All cover national private-industry manufacturing and
   are not seasonally adjusted. ECI units are index, December 2005=100; ECEC units
   dollars/hour worked. Monthly wage observations link to the same reference
   quarter. All values retain quarterly frequency and current retrieval vintage.
   Total/wage/benefit levels are reconciled within rounding tolerance. Future
   quarters are explicitly unavailable; missing historical data or provider errors
   remain pending. No interpolation, universal benefit multiplier or company
   fully loaded labor-cost claim is generated. CES and ECEC hour denominators differ.
3. **Company exposure.** Read-only TLS RDS snapshots retain companies, products,
   relationships, product attributes and evidence. An eligible association requires
   a current verified manufacturer role plus a reviewed US manufacturing site with
   evidence and explicit operator company ID. Domicile, sector and commercial
   territory are insufficient. Other relationships become review candidates;
   historical exposure remains unverified. The current connected tracking
   directory is empty, so its zero company/product coverage is explicitly reported.
   Daily snapshots refresh as the registry is populated. No RDS inserts/updates.

Source responses and join-cache provenance are persisted in S3. Successful join
lookups cache for 24 hours, failed lookups for one hour. The quarterly panel is
shared across all monthly pages to limit API use. The retained CES definitions and
public API catalog limitation remain explicit. Empty footnotes do not prove finality.

## Expanded backfill and notification

`config/bls-enrichment-backfill.json` now selects
`bls-enrichment-backfill-2026-10-18-v2`. This supersedes the original wage-only job;
its timer/service were stopped before scope migration. The original registry,
outputs, config and scope remain preserved. The expanded job reprocesses all
69 distinct saved monthly versions represented by 168 original observations in
17 pinned batches, January 2021–September 2026. Today's original CES lookup evidence
is reused, while all three joins are newly assessed. Release-input checksums are
pinned in the config. Original record identity, values, event dates and source
lineage remain intact. New context is not reconstructed historical API availability.

The existing five-minute bounded systemd timer resumes the expanded job. A failed
join never becomes a completed gap. After all versions have successful assessments,
committed batch publication and exact job-specific Athena counts are checked.
Only then does SNS send the completion email to the existing confirmed
`randall@optima-holdings.com` subscription. The email reports per-join outcomes,
the cancelled release, not-yet-available quarters, RDS empty-directory counts,
and temporal limitations. Empty RDS scope produces `complete_with_limitations`,
not a claim that companies were matched. Connectivity or retrieval errors stay
pending and do not send a completion email.

Progress: `reports/bls-enrichment-backfill-2026-10-18-v2-latest.json`.
Event use and pending routing: S59 section of `ENTITY_DISCOVERY_ROLLOUT_PLAN.md#event-pipeline`.
