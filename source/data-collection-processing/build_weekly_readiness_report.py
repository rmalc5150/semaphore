"""Render the evidence-backed source inventory and remaining implementation work."""
import csv
import json
from collections import Counter
from pathlib import Path

from weekly_readiness import ROOT, OUT, now, save


NEXT = {
 'S01': 'Resolve 388 pending identities; reconcile collector universes 0.2/0.3/0.5 against the 496 enabled company IDs and dated admission records.',
 'S02': 'Reconcile entitled exchange inventory and profile fields for the enabled universe; distinguish current snapshots from historical fundamentals.',
 'S03': 'Adjudicate each unresolved symbol/window with listing/session evidence; retain existing pre-IPO and holiday exclusions and never reset the forward cursor.',
 'S04': 'Declare the HKEX listing cohort requiring independent price verification and reconcile it against EODHD rather than double-counting.',
 'S05': 'Provisional pilot benchmarks XBI/BOTZ/SOXX/LIT and USD/EUR/USD/JPY; verify entitlements, inception dates, adjustments and local sessions before acceptance.',
 'S06': 'Capture one dated official BOTZ/SOXX/LIT holdings edition; inventory 2021-present archived editions and security mappings separately.',
 'S07': 'Reconcile accession/exhibit inventory for reviewed CIKs and 2021-present windows; bounded recent and older receipt field checks passed.',
 'S08': 'Capture companyfacts for one verified CIK, check units/periods/amendments and trace custom-tag gaps to original financial notes.',
 'S09': 'Check one nonempty original announcement/document and full requested title/date/language inventory; do not equate SEC holdings with HKEX completeness.',
 'S10': 'Choose tracked CNINFO issuers and EDINET filer IDs from the reviewed listings, then verify current access and one original filing per jurisdiction.',
 'S11': 'Extend saved Moderna product and QuantumScape careers evidence to issuer/customer/lender allowlists; validate each domain and original dated document.',
 'S12': 'Optional enrichment deferred: document existing license/sample export or use disclosed funding documents; do not purchase a dataset.',
 'S13': 'Verify recent-only Finlight plan boundaries and source/company matching; 2021 history requires an explicit archive decision.',
 'S14': 'Continue existing Marketaux checkpoint at 2021-02-26 under its request budget; resolve pending reconciliation and join raw windows to publication receipts.',
 'S15': 'Expand nonempty personnel samples across the 12-company pilot; validate false positives, archive source dates and original announcement lineage.',
 'S16': 'Identify an entitled analyst-estimate export for the pilot companies, including vintage/revision times; account access and retrospective history remain unverified.',
 'S17': 'Use Moderna COVE NCT04470427 as a named pilot; validate protocol/results/sites/attachments and dated historical versions, not just the current registration.',
 'S18': 'Select corresponding EU trial IDs; inspect captured CTIS fields, site/protocol/result versions and public document accessibility.',
 'S19': 'Original SPIKEVAX FDA review is captured and parsed into 30 pages; verify current action/CRL coverage and original decision links across selected products.',
 'S20': 'Register a separate Drugs@FDA review/label package for an in-scope small-molecule product; CBER SPIKEVAX evidence does not establish Drugs@FDA coverage.',
 'S21': 'Capture the original EMA Spikevax EPAR/label version and assessment annexes; reconcile editions and availability dates.',
 'S22': 'Inspect a needed original MHRA public assessment alongside ILAP/orphan lists; explicitly inventory indications and historical decision versions.',
 'S23': 'Select a PMDA product/approval ID and capture the original Japanese review; designation-list records alone do not provide methods or labels.',
 'S24': 'Capture the original Health Canada Spikevax NOC/decision/label with DIN and publication date; register the dedicated adapter/publication route.',
 'S25': 'Define named ChiCTR registrations and reconcile detail/history fields; deploy its pending recurring reconciliation after sample acceptance.',
 'S26': 'Resume the preserved NMPA checkpoint only after gateway HTTP 429 clears; reconcile inventory and deterministic detail cohorts separately. No cursor reset or repeated paid restart.',
 'S27': 'PubMed search and three original abstracts are saved; add named COVE references, correction/retraction links, cursor/count reconciliation and shared manifests.',
 'S28': 'Two original Europe PMC full texts and licenses are saved; capture COVE methods/supplements and version corrections, review per-article reuse, then enable bounded incremental publication.',
 'S29': 'Continue Crossref historical cursor 2022-10-09; inspect DOI/date-basis/version gaps and reconcile proceeding windows, not just min/max dates.',
 'S30': 'Choose a named ASCO/AACR or ICRA conference and year relevant to the pilot; save original program/poster/abstract IDs, disclosures and access restrictions.',
 'S31': 'Declare UK indication-specific guidance scope. Keep NICE out of training exports; use permitted links/metadata or an approved alternative with its own rights.',
 'S32': 'Declare US Medicare indication/geography scope; retrieve an original NCD/LCD edition with effective dates and revision history.',
 'S33': 'Identify an original specialty-society/payer policy for the selected indication and country; verify redistribution/training rights and historical editions.',
 'S34': 'Choose US investigators from original trial/paper IDs and payment years 2021-2025; resolve person/company IDs and downloaded edition/revision definitions.',
 'S35': 'Scope original FDA inspection/warning-letter records to selected manufacturers/sites; record event/result/resolution dates and entity-match uncertainty.',
 'S36': 'Choose named COVE-associated investigators/institutions and NIH fiscal years 2021-2026; validate public project IDs, funding units, linked papers and observed release times.',
 'S37': 'Build NIAID and named COVE investigator-site allowlists from original affiliations; validate ownership and dated institutional evidence before network claims.',
 'S38': '57 months / 4,401,374 global patent publications verified in production; continue partial October 2025 window and reconcile the remaining requested months and party joins.',
 'S39': 'Daily USPTO cursor reaches October 9; verify raw parent hashes/fields and required curated publication. Raw daily application records do not become global-history Athena rows.',
 'S40': 'Review original assignment parties/effective dates and unresolved entity links for the selected company IDs; patent applicant does not prove current legal ownership.',
 'S41': 'Verify an existing SAM.gov API entitlement and selected opportunity/NAICS/entity scope; original attachments and version inventory require an adapter.',
 'S42': 'Define EU buyer/supplier and CPV/language scope; test one original TED notice, pagination, corrections and tender-to-award linkage.',
 'S43': 'Recipient-specific Intel search returns two exact-name candidates and one different recipient; resolve UEI/legal identity and capture award detail/transaction history before acceptance.',
 'S44': 'Find Greenhouse board IDs from original employer careers links; QuantumScape uses its own careers/jobs2web surface and is not evidence of a Greenhouse board.',
 'S45': 'Find Lever site IDs through original employer links and capture prospective IDs/first-seen times; no known-board assumption or reconstructed vacancy history.',
 'S46': 'Intel official GitHub evidence and LLVM releases/licenses are saved; pin tag/commit identifiers, verify repository ownership and capture compatibility changes.',
 'S47': 'Select one relevant NIST robotics test method plus a disclosed independent/customer result; declare version/task/exposure/comparator, not an invented universal score.',
 'S48': 'Intel MLPerf v5.1 system and original performance log are saved; pin repository revision and pair workload/scenario/precision/quality/power with the system configuration.',
 'S49': 'Capture an original selected vendor/lab datasheet or deployment report; retain product/model/version, units and measured exposure. Missing yield/uptime remains unknown.',
 'S50': 'Choose actual consumer/medical/industrial product models and jurisdictions; verify CPSC or the appropriate authority, original recall IDs and affected-unit denominators.',
 'S51': 'Three original Federal Register battery-document records are saved; distinguish proposed/final rules and capture amendment/effective-date documents and other jurisdictions.',
 'S52': 'Save an official ITA CSL edition and declare foreign-list jurisdictions; resolve entity/alias matching and effective list changes independently.',
 'S53': 'Scope USGS lithium/nickel/cobalt/graphite country tables and 2021-2026 editions; save an original edition and distinguish mine/refining production and units.',
 'S54': 'Provisional pilot: US reporter 842, China partner 156, imports, HS 850760, 2021-2025; verify HS edition, value/quantity units and endpoint entitlement before collection.',
 'S55': 'Save the original DOE storage cost/performance edition and model; declare lithium-ion duration/usable-capacity/cost boundary assumptions rather than current vendor pricing.',
 'S56': 'Five battery-generator records from the valid August 2026 EIA workbook are published; September URL returned HTML and was rejected. Reconcile editions, plant/generator IDs, MW/MWh and revision dates.',
 'S57': 'Provisional bounded sample: CAISO TH_NP15_GEN-APND, day-ahead LMP, one completed day; verify node relevance, local/DST intervals and components before broader history.',
 'S58': 'Select actual pilot-company project/site and operator/utility jurisdictions; capture original queue/tariff/permit editions with project IDs and milestone dates.',
 'S59': '24 manufacturing earnings observations (CES3000000003, 2024-2025) are saved; verify geography/seasonal adjustment/units and extend 2021-present with release vintages.',
 'S60': 'Optional SEMI detailed data deferred unless an existing license/export is available; public summaries remain discovery leads.',
 'S61': 'Optional IFR detailed annual statistics deferred pending an existing license/sample and required geography/application/year definitions.',
 'S62': 'User deferred paid teardown/material-price acquisition for cost on 2026-10-11; document missing fields and evaluate public evidence without assuming equivalence.',
 'S63': 'User deferred Reddit acquisition for cost on 2026-10-11; omit Reddit-dependent features from current scope; no purchase task.',
 'S64': 'Fresh public Bluesky search returned HTTP 403; record the access blocker and test an authorized route if needed. Reddit acquisition is deferred; other social inputs do not establish Reddit coverage.',
 'S65': 'Weekly fixed 12-query US/English search capture is approved and enabled; reconcile 104 missing keyword-month cells, monthly revisions and unsupported ranking history. Expand only after scope acceptance.',
 'S66': 'Google Trends API application submitted October 11; await approval and credentials. DataForSEO remains a distinct provider; historical scope must be verified after approval.',
 'S67': 'Optional private operational/patient/customer data deferred pending named owner, permitted aggregate sample and agreement; unavailable private metrics stay unknown.',
}


def main():
    baseline = list(csv.DictReader((ROOT / 'reports/specialist-source-checklist-2026-10-05.csv').open()))
    publication = json.loads((OUT / 'publication.json').read_text())
    scope = json.loads((OUT / 'scope.json').read_text())
    audit = json.loads((OUT / 'live-audit.json').read_text())
    counts = Counter()
    for source, dataset, count in publication['expected_counts']:
        counts[source] += int(count)
    optional = {'S12', 'S60', 'S61', 'S62', 'S64', 'S66', 'S67'}
    rows = []
    for row in baseline:
        source = row['source_id_name_and_data'][:3]
        status = 'partial' if counts[source] or 'Partial' in row['holdings_and_athena'] or 'Q' in row['holdings_and_athena'] else 'not_started'
        if source in ('S26', 'S63', 'S64'):
            status = 'blocked'
        if source in optional and not counts[source] and source != 'S64':
            status = 'optional_deferred'
        next_week = '2026-10-12' if source in ('S01','S03','S14','S26','S38','S39','S63','S65') else ('2026-10-13' if 17 <= int(source[1:]) <= 37 else ('2026-10-16' if source in optional else '2026-10-14'))
        rows.append({**row, 'source_id': source, 'reviewed_at': now(), 'status': status,
            'requirement_decision': 'optional deferred unless existing entitlement makes it necessary' if source in optional else 'required existing scope retained; exact entity/jurisdiction sub-scope still provisional',
            'universe_version': scope['universe_version'], 'history_complete': False,
            'new_sample_rows': counts[source], 'new_sample_athena_route': publication['database'] + '.' + publication['table'] if counts[source] else '',
            'new_sample_release_id': publication['release_id'] if counts[source] else '',
            'new_verification_query_id': publication['query']['query_id'] if counts[source] else '',
            'evidence': 'publication.json; sample-coverage.json; captures/' if counts[source] else 'live-audit.json; existing-field-samples.json; October 5 baseline (provider access not newly verified)',
            'owner': 'developer with Codex', 'next_action': NEXT[source], 'review_date': next_week,
            'acceptance_test': row['verification_required'] + '; immutable raw/hash/count evidence, bounded publication query, replay/resume and explicit missing history required',
            'rights_status': 'source-specific use review required; new pilot rows excluded from training',
            'expected_windows': None, 'completed_windows': None, 'unattempted_windows': None})
    assert len(rows) == 67 and len(NEXT) == 67
    save('source-acceptance-records.json', rows)
    with (OUT / 'source-checklist.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    lines = ['# Data sources to check and how', '',
        'Updated October 9, 2026. This list retains all 67 sources and their provider-specific checks. The global enabled universe is provisional; samples cover three verified companies per sector. No source is certified complete for 2021-present history.', '',
        '[Filterable CSV](source-checklist.csv) · [Acceptance records](source-acceptance-records.json) · [Original endpoint catalog](../../../specialist_data_collection_plan.md#api-and-site-access-catalog)', '',
        'For each source: declare entity/query/date scope; verify original IDs, dates, fields and rights; save immutable raw evidence and hashes; reconcile required versus committed versus published windows; compare a bounded Athena query to manifest counts; test replay and revisions. Retain unsupported history, verified-empty responses and explained exclusions separately. The shared sample table is a pilot publication, not the provider’s production table.', '',
        '| Source | Where and how to check | Current decision | First remaining task and acceptance |',
        '|---|---|---|---|']
    def cell(text):
        return str(text).replace('|', '\\|').replace('\n', ' ')
    for row in rows:
        lines.append('| ' + ' | '.join(map(cell, [row['source_id_name_and_data'], row['planned_acquisition'] + ' Check: ' + row['verification_required'],
            row['status'] + (f"; {row['new_sample_rows']} new query-verified sample rows" if row['new_sample_rows'] else '; see baseline and live evidence'),
            NEXT[row['source_id']] + ' Review: ' + row['review_date']])) + ' |')
    (OUT / 'data-sources-and-checks.md').write_text('\n'.join(lines) + '\n')
    progress = []
    for key, value in audit['progress'].items():
        if isinstance(value, dict) and value.get('next_date'):
            progress.append({'key': key, 'next_date': value['next_date'], 'updated_at': value.get('updated_at'),
                'status': value.get('status'), 'last_manifest': value.get('last_manifest') or value.get('last_complete',{}).get('manifest'),
                'interpretation': 'Configured stream watermark, not source-wide usable-history certification. Keep old universe epochs separate.'})
    save('required-window-ledger.json', {'scope': 'Existing readable stream watermarks and explicit remaining source actions; unknown entity-by-window denominators remain null.',
        'stream_progress': progress, 'keyword_month_ledger': 'keyword-history-window-ledger.csv',
        'patent_months': {'completed_and_published': 57, 'publications': 4401374, 'next_date': '2025-10-01', 'partial_window': '2025-10'},
        'source_counts_are_not_history_completion': True})
    report = f'''# Weekly source readiness and completed work

October 9, 2026. The source inventory and bounded pilots are complete; broad source/history acceptance remains partial. The global universe contains {len(scope['required_companies'])} enabled companies and {scope['pending_identities']} pending identities. The pilot uses 12 verified companies, three per sector, with US/English search as an explicit sample assumption.

## Completed checks and captures

- Reviewed all S01–S67 rows and recorded requirement decisions, provider-specific checks, evidence, owner, first remaining task and October 12–16 review date in [the source list](data-sources-and-checks.md) and [CSV](source-checklist.csv).
- Executed 18 successful bounded recent/earlier publication queries across Q1–Q9. Inspected fields in 16 recent/earlier windows and separately checked nonempty disclosure and personnel releases. Earlier receipts are not a January 2021 coverage audit. [Live audit](live-audit.json), [field samples](existing-field-samples.json), [nonempty checks](nonempty-field-samples.json).
- Completed DataForSEO keyword history, trends and 12 desktop Google organic snapshots. Actual total provider cost: **USD 0.03864**. Repeated pilot execution used saved responses with no additional paid requests. [Cost](dataforseo-cost.json), [query scope](scope.json), [date coverage](sample-coverage.json).
- Published **{publication['rows']} normalized rows** spanning {len(counts)} source IDs after raw S3 hash read-back and Parquet round-trip verification. Athena returned the expected count for every source/dataset group. Table: `{publication['database']}.{publication['table']}`; workgroup `{publication['workgroup']}`; filter `release_id='{publication['release_id']}'`. [Publication and query receipts](publication.json).
- Captured PubMed abstracts and recent/older Europe PMC original full text, methods, supplement references and license text; captured Moderna COVE registration and literature metadata. Correction/retraction links and complete cohort/version inventory remain partial.
- Captured and parsed the original SPIKEVAX FDA review into 30 evidence pages. This CBER document does not certify Drugs@FDA or broader FDA history.
- Captured procurement search candidates, Intel original repository/release/license evidence, an MLPerf v5.1 original performance log and system configuration, three Federal Register rulemaking records, five battery-generator inventory records, and 24 monthly manufacturing earnings observations.
- Prepared and validated weekly capture code and systemd units. The user explicitly approved recurring capture; the timer is **enabled and active**, Friday **11:00 Europe/Madrid** plus up to five minutes jitter. Verified next run: **October 16, 2026, 11:01:48 Europe/Madrid**. It shares `.heavy-job.lock` and `optima-data.slice`, caps memory at 256 MiB and stops additional requests at the USD 1 run budget. Keyword metrics are captured monthly; snapshots/trends weekly. Two automatic cycles are not yet observed. [Timer verification](search-timer-status.txt).
- Five meaningful contract tests passed: no paid replay, no automatic retry of ambiguous paid requests, failed-HTTP exclusion, separate paths sharing a blob, and rejecting HTML masquerading as an XLSX workbook. Systemd unit verification passed.

## Coverage findings and blockers

Daily USPTO collection has reached an exclusive cursor of October 9. Global patent history has 57 published months and 4,401,374 publications through September 2025; October 2025 is partial. These are different datasets. Crossref history is at October 9, 2022; Marketaux history is at February 26, 2021. Existing source quotas, locks, timers, cursors and explained market exclusions are retained. [Window ledger](required-window-ledger.json).

NMPA's preserved partial inventory has 7,802 records and next page 395; its latest saved page passed SHA-256 and row-count checks. The current gateway failure is HTTP 429, with stalled progress after its last verified page on October 7. The old page-148 parser problem is superseded; do not submit the old 202 support draft as a description of the fresh failure. No provider support message was sent. Resume the preserved checkpoint after access recovers; inventory and detail/history completion remain separate. [Current health](health.json), [checkpoint](nmpa-checkpoint.json).

The keyword-history ledger contains 828 expected keyword-month cells through September 2026 and **104 not returned**. Some actual returned histories include July 2021 despite documentation describing August 2021 as the general start; preserve those actual dates without assuming earlier complete history. Trends returned a different relative-interest series; present-day SERPs supply no historical ranking observations. [Exact keyword ledger](keyword-history-window-ledger.csv).

USAspending keyword search returned unrelated recipients. Recipient-specific Intel search includes two exact-name candidates and another recipient; none is accepted as a confirmed company award without identifier/detail review. MLPerf directory listings are distinguished from the captured performance log. An EIA September workbook URL returned HTML with HTTP 200 and was rejected; the valid August workbook supplies the five accepted battery samples. Bluesky still returns HTTP 403; authorized Reddit access/history is unresolved. New sample rows remain excluded from training until source-specific reuse and point-in-time acceptance.

## Remaining work ordered for October 12 to 16

1. October 12: reconcile identity/universe changes, market gaps, NMPA access and the remaining patent/news history; Reddit acquisition is deferred. Inspect quotas and current locks before resuming any collector.
2. October 13: integrate accepted literature/FDA evidence into shared collection manifests and bounded recurring publication; assess every trial/regulatory source's protocol/SAP/result/site/version gaps. Keep NICE out of training exports.
3. October 14: complete recipient-ID procurement details, pin benchmark revisions/configurations, implement original employer-board and technical adapters, and reconcile selected EIA/BLS editions and units.
4. October 15: implement declared policy/material/trade/energy series and project scopes with original evidence; optional licensed/private acquisitions remain deferred.
5. October 16: inspect the first scheduled search cycle and its publication receipt; reconcile required versus completed/verified-empty/excluded/unavailable/failed/unattempted windows, then review the 12-company field/identity sample independently from the 496-company universe.

Each S01–S67 source has its own acceptance test and first task in [the acceptance records](source-acceptance-records.json). Full January 2021-present history, every required jurisdiction/field, complete entity joins and two scheduled capture cycles remain open. The January 15 delivery goal remains unchanged.
'''
    (OUT / 'readiness-report.md').write_text(report)
    print(json.dumps({'source_rows': len(rows), 'sample_rows': publication['rows'], 'statuses': dict(Counter(r['status'] for r in rows))}))


if __name__ == '__main__':
    main()
