"""Reviewable layer requirements and acquisition routes, without claiming readiness."""
import csv
import json
from collections import defaultdict, Counter
from datetime import date
from pathlib import Path
from research_contract import ROOT, load_json
from specialist_plan import jobs

OUT = ROOT / 'reports/specialist-expansion-2026-10-09'
LAYERS = [
 ('B1','Biotech','Comparator Credibility','S17 S18 S19 S20 S21 S27 S28 S29 S30 S31 S32 S33 S67',
  'indication; patient population; protocol and SAP versions; randomized comparator; endpoint definition and effect/CI; missingness and multiplicity; independent review and guideline dates',
  'registry/protocol/product links; licensed guidelines; unavailable SAP or patient-level analysis; full-text extraction and dated rights'),
 ('B2','Biotech','Western Validation','S11 S17 S18 S19 S21 S28 S29 S30 S36 S37 S43 S68',
  'named institution; grant ID and award amount/currency/fiscal year; collaboration role; committed vs awarded vs spent funding; trial validation stage; independent replication',
  'company subsidiaries and independent institutional relationships; non-US grants and original collaboration contracts'),
 ('B3','Biotech','Key Opinion Leaders','S15 S27 S28 S29 S30 S34 S37 S68',
  'person identity; affiliation and effective dates; authorship role; investigator/site links; disclosure and payment recipient/payer/type/date/amount; correction/retraction history',
  'CMS payment rows and ownership/research tables; person disambiguation; global disclosures; historical affiliation evidence'),
 ('B4','Biotech','Talent Migration','S07 S09 S10 S11 S15 S29 S30 S37 S44 S45',
  'person and employer IDs; role/location; hire/exit/first-observed dates; vacancy counts and role mix; operating milestones and hiring-to-milestone lag',
  'verified employer board IDs and vacancy archives; private moves and unavailable historical staff rosters'),
 ('B5','Biotech','Trial Quality','S17 S18 S19 S25 S26 S27 S28 S35 S37 S67 S68',
  'site and PI identity; geographic exposure; planned/actual enrollment; protocol changes; recruitment/completion/retention; safety/compliance findings; query rate and audit denominators',
  'private CRO/site metrics; FDA inspection classifications; China access throttling; site infrastructure and dated joins'),
 ('R1','Robotics','Task Advantage and Comparator Credibility','S11 S46 S47 S49 S59 S61 S67',
  'device/version; task/environment/payload; throughput/accuracy; intervention and downtime denominator; comparator conditions; utilization; labor/maintenance/energy and fully loaded cost',
  'customer/lab measurements and fleet denominators; non-US wages; product/task identities and total operating costs'),
 ('R2','Robotics','Customer Commitment and Deployment Expansion','S07 S08 S09 S10 S11 S41 S42 S43 S61 S67',
  'customer/site identity; procurement stage; contract/option/award/obligation/paid dates; committed value/currency; deployment count; repeat orders and customer finance',
  'SAM API key; original notice XML and transaction follow-through; global/private procurement and deployment counts'),
 ('R3','Robotics','Workflow Integration and Distribution','S11 S38 S46 S49 S67',
  'SDK/release date and commit; device/OS/middleware compatibility; integration status; partner identity; distribution channel; support/license terms; switching costs',
  'named repository and vendor coverage; original compatibility tests and commercial integration/customer evidence'),
 ('R4','Robotics','Talent Migration and Execution Readiness','S07 S08 S09 S10 S11 S15 S44 S45 S46',
  'person/role movement dates; engineering/support vacancies; prototype/certification/production milestone; hiring lag; execution delays; financing capacity',
  'employer board mapping, historical vacancies and dated product/production milestones'),
 ('R5','Robotics','Fleet Reliability, Production and Warranty','S07 S08 S09 S10 S11 S47 S49 S50 S61 S67',
  'fleet exposure hours/units; failures and repair time; incident/recall IDs and affected models; warranty provision/service liability; manufacturing throughput and service network',
  'CPSC access currently HTTP403; private telemetry and failure denominators; full filing-note extraction; licensed installed-fleet statistics'),
 ('S1','Semiconductors','Application Advantage and Benchmark Credibility','S11 S46 S48 S49 S62',
  'chip/system/version; workload and MLPerf edition; precision/sparsity/batch; accuracy/latency/throughput; measured power and price; compiler settings; comparator reproducibility',
  'full MLPerf edition/system/config index; non-AI benchmarks; licensed teardown and reproducible application costs'),
 ('S2','Semiconductors','Qualification and Design-Win Conversion','S07 S08 S09 S10 S11 S41 S42 S43 S49 S62 S67',
  'customer/program/chip identity; sampled vs qualified vs designed-in vs shipped; dated orders and revenue conversion; cancellation; customer concentration and certification conditions',
  'customer disclosure coverage; private qualification/order data; teardown rights and dated design-win links'),
 ('S3','Semiconductors','Ecosystem Position and Value Capture','S07 S08 S11 S29 S38 S39 S40 S46 S51 S52 S54 S60',
  'ISA/toolchain/IP linkage; patents and assignments; ecosystem adoption; licensing/royalty terms; export policy stage/effective date; restricted counterparty and trade exposure',
  'historical screening-list vintages; international trade-control notices; IP licensing contracts; current lists cannot reconstruct past restrictions'),
 ('S4','Semiconductors','Talent Migration and Development Execution','S07 S08 S09 S10 S11 S15 S29 S30 S38 S44 S45 S46',
  'engineering hire/exit and role mix; tapeout/first silicon/qualification/ship dates; process node and foundry; revision delays and development financing',
  'dated chip/program identity, vacancy archives and undisclosed tapeout/revision milestones'),
 ('S5','Semiconductors','Manufacturing and Supply Scalability','S07 S08 S09 S10 S11 S43 S49 S54 S60 S62 S67',
  'fab/package/test site; node/capacity/utilization; yield and defect denominator; inventory/lead time; wafer/packaging cost; supplier concentration and committed capacity',
  'private yields/capacity economics; licensed SEMI/teardown; filing-note extraction; HS trade is not company-level manufacturing yield'),
 ('E1','Energy storage','Application Value and Comparator Credibility','S11 S38 S49 S53 S55 S56 S57 S62 S67',
  'chemistry/system/application; cycle/calendar life and test temperature/DoD; round-trip efficiency; power/energy units; installed costs; degradation; comparator levelized cost conditions',
  'independent product tests; structured DOE cost/performance tables; project-specific degradation and comparator assumptions'),
 ('E2','Energy storage','Geopolitics, Material Access and Supply Resilience','S07 S08 S11 S38 S51 S52 S53 S54 S55 S62 S67',
  'material/grade/geography; reserves/production/imports with HS/version/unit; origin and concentration; offtake/volume/price formula; policy stage/effective dates; supplier substitution',
  'global reporter/flow/partner coverage; licensed grade-specific prices and offtakes; historical sanctions lists; numeric USGS table extraction'),
 ('E3','Energy storage','Customer Commitment and Project Bankability','S07 S08 S09 S10 S11 S41 S42 S43 S55 S56 S58 S67',
  'project/customer/lender IDs; capacity/location; awarded vs financed vs under-construction vs operating; debt/equity/guarantee terms; contract value; permitting/interconnection status',
  'project registry, lenders and private contracts; global utility/permit coverage; financing terms and original procurement stages'),
 ('E4','Energy storage','Substitution, Market Access and Revenue Durability','S11 S38 S49 S51 S53 S54 S55 S56 S57 S58 S62 S67',
  'substitute performance/material cost; queue/permit milestones; market rules; interval energy and ancillary prices; dispatched quantities/SOC; revenue contract and degradation assumptions',
  'CAISO pre-retention downloader and ancillary products; queues/permits; other grid markets; private dispatch/SOC and contracted revenues'),
 ('E5','Energy storage','Financing Runway and Talent Migration','S07 S08 S09 S10 S11 S15 S41 S42 S43 S44 S45 S55 S56',
  'cash/debt/burn/capex and filing availability; financing covenant/terms; plant milestones; engineering/production hires and vacancies; dilution and runway assumptions',
  'structured debt/covenant/warranty notes; private financing; employer boards and historical plant/employment milestones'),
]

URLS = {
 'S01':'https://www.sec.gov/search-filings/edgar-application-programming-interfaces',
 'S02':'https://eodhd.com/financial-apis/', 'S03':'https://eodhd.com/financial-apis/',
 'S04':'https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities?sc_lang=en',
 'S05':'https://eodhd.com/financial-apis/', 'S06':'https://www.ishares.com/us/products/etf-investments',
 'S07':'https://www.sec.gov/search-filings/edgar-application-programming-interfaces',
 'S08':'https://www.sec.gov/search-filings/edgar-application-programming-interfaces',
 'S09':'https://www1.hkexnews.hk/search/titlesearch.xhtml?lang=en',
 'S10':'https://www.cninfo.com.cn/; https://disclosure2.edinet-fsa.go.jp/',
 'S11':'verified issuer/customer/lender/utility domains in the company universe and disclosure source configuration; original documents only',
 'S12':'https://data.crunchbase.com/docs', 'S13':'https://finlight.me/', 'S14':'https://www.marketaux.com/documentation',
 'S15':'original employer/institution news RSS and personnel archives in config; approved feeds only',
 'S16':'named licensed analyst provider required; no public API can supply proprietary historical analyst vintages',
 'S17':'https://clinicaltrials.gov/data-api/api', 'S18':'https://euclinicaltrials.eu/',
 'S19':'https://open.fda.gov/apis/; https://www.fda.gov/vaccines-blood-biologics',
 'S21':'https://www.ema.europa.eu/en/medicines/download-medicine-data',
 'S22':'https://www.gov.uk/government/organisations/medicines-and-healthcare-products-regulatory-agency',
 'S23':'https://www.pmda.go.jp/english/', 'S24':'https://health-products.canada.ca/noc-ac/index-eng.jsp',
 'S25':'https://www.chictr.org.cn/', 'S26':'https://www.chinadrugtrials.org.cn/',
 'S29':'https://api.crossref.org/swagger-ui/index.html',
 'S30':'original meeting/program domains in conference configuration; organiser-specific archives, no universal API',
 'S31':'https://www.nice.org.uk/reusing-our-content',
 'S33':'named society/payer guideline publisher and permitted original version archive required',
 'S37':'original institution sites resolved through ROR and publications; institution-specific archives',
 'S38':'https://console.cloud.google.com/marketplace/product/google_patents_public_datasets/google-patents-public-data',
 'S39':'https://data.uspto.gov/', 'S40':'https://assignmentcenter.uspto.gov/',
 'S49':'verified vendor/laboratory original product and technical-document URLs; no universal endpoint',
 'S66':'https://trends.google.com/trends/',
 'S67':'named sponsor/CRO/site/customer/fab/project data owner required; permitted aggregate export/API after agreement',
 'S20':'https://www.fda.gov/drugs/drug-approvals-and-databases/drugsfda-data-files',
 'S32':'https://api.coverage.cms.gov/docs/', 'S34':'https://openpaymentsdata.cms.gov/about/api',
 'S35':'https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/inspection-classification-database',
 'S36':'https://api.reporter.nih.gov/', 'S41':'https://open.gsa.gov/api/get-opportunities-public-api/',
 'S42':'https://docs.ted.europa.eu/api/latest/search.html', 'S43':'https://api.usaspending.gov/docs/',
 'S44':'https://developers.greenhouse.io/job-board.html', 'S45':'https://github.com/lever/postings-api',
 'S46':'https://docs.github.com/en/rest/releases/releases', 'S47':'https://www.nist.gov/el/robotics',
 'S48':'https://github.com/mlcommons', 'S50':'https://www.cpsc.gov/Recalls/CPSC-Recalls-Application-Program-Interface-API-Information',
 'S51':'https://www.federalregister.gov/developers/documentation/api/v1',
 'S52':'https://www.trade.gov/consolidated-screening-list',
 'S53':'https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries',
 'S54':'https://uncomtrade.org/docs/un-comtrade-api/', 'S55':'https://www.energy.gov/oe/energy-storage',
 'S56':'https://www.eia.gov/electricity/data/eia860m/',
 'S57':'https://www.caiso.com/notices/new-tool-now-available-on-caiso-oasis-website',
 'S58':'https://www.caiso.com/generation-transmission/generation/generator-interconnection/interconnection-queue',
 'S59':'https://www.bls.gov/developers/api_signature_v2.htm', 'S60':'https://www.semi.org/en/products-services/market-intelligence',
 'S61':'https://ifr.org/worldrobotics', 'S62':'https://www.techinsights.com/',
 'S63':'https://support.reddithelp.com/hc/en-us/articles/14945211791892-Reddit-API-Access',
 'S64':'https://docs.bsky.app/', 'S65':'https://docs.dataforseo.com/v3/',
 'S68':'https://ror.readme.io/docs/rest-api',
 'S27':'https://www.ncbi.nlm.nih.gov/books/NBK25501/',
 'S28':'https://europepmc.org/RestfulWebService',
}

NEXT = {
 'S28':'Review topic/indication coverage, original article licenses, comparator/SAP/methods extraction and correction history; finish queued open-access XML and dated product/trial links.',
 'S32':'Review national Medicare document/version/effective-date coverage and queued originals; add LCD/commercial payer and non-US scope, revision histories and content-use constraints.',
 'S34':'Review captured annual edition catalogue. Filtered payment queries remain unverified; resolve investigator/person IDs and manufacturer subsidiaries before accepting payment/disclosure coverage.',
 'S36':'Review bounded company-name batches and grant topics, NIH fiscal-year boundaries, USD funding fields and independent institution links; daily additions use seven-day overlap, monthly full-year revision checks.',
 'S42':'Review four CPV categories, buyer/supplier identities, currencies, notice-language coverage and procurement stage; retain all original notice versions and finish XML/transaction follow-through.',
 'S43':'Review recipient name candidates against UEI/legal subsidiaries and award stage; finish transaction/obligation/payment detail and non-contract/grant/loan and non-US coverage.',
 'S46':'Review ownership of the five SDK repositories, complete release pages, product/version compatibility and commercial integration evidence; remain within shared public GitHub budget.',
 'S47':'Review the original NIST robotics methods and task conditions; discovery page capture still needs method documents plus actual disclosed independent/customer measurements.',
 'S48':'Review commit-pinned measured results/units/accuracy/power conditions and original-log/system-config queues across 12 editions; complete product/chip identities and non-AI application tests.',
 'S51':'Review topic/jurisdiction coverage and proposed/final/amended/effective stages; retain original policy documents and corrections, and add non-US regulators.',
 'S52':'Review current CSL identities, aliases and list-source fields; obtain verifiable historical list editions and foreign lists. Current list membership is not past restriction status.',
 'S53':'Review lithium/cobalt/nickel/graphite annual editions and country/unit/production definitions; extract numerical tables and distinguish estimates/revisions from publication timing.',
 'S54':'Review five reporter countries, four HS commodities and total-world import flow, classification versions, value/mass/quantity units and reporting lags; global partner/export/grade scope remains missing.',
 'S55':'Review original DOE cost/performance report and assumptions; programme-page discovery does not supply structured installed-cost, duration, degradation or application comparator fields.',
 'S56':'Review all discovered valid battery-workbook months, plant/generator identity, MW/MWh headers and revisions; daily checks try the latest three linked periods and reject missing/HTML files.',
 'S57':'Review both CAISO hubs, DAM component units, UTC/local/DST intervals and missing intervals; integrate the pre-39-month Historical OASIS downloader, ancillary markets and other grid jurisdictions.',
 'S59':'Review manufacturing hourly-earnings seasonality, USD/hour and month periods; complete 2021 onward archives and release revisions, plus relevant other countries and fully loaded labor costs.',
 'S65':'Review daily accepted 12-query capture and monthly metrics under USD1 per-run cap; a full company/product/geography grid and actual historical SERP rankings remain unavailable/unimplemented.',
}


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan = load_json(ROOT / 'config/specialist-inputs.json')
    universe = load_json(ROOT / 'config/company-universe.v0.5.json')
    scheduled = defaultdict(list)
    for s in plan['sources']:
        if s.get('enabled'):
            scheduled[s['source_id']].append(s)
    probes = load_json(OUT / 'schema-probes.json') if (OUT / 'schema-probes.json').exists() else []
    probe_by_mode = {(r['source'], r['job']['mode']): r for r in probes}
    if (OUT / 'schema-repairs.json').exists():
        probe_by_mode.update({(r['source'], r['job']['mode']): r for r in load_json(OUT / 'schema-repairs.json')})
    mapping = defaultdict(list)
    layer_rows = []
    for code, sector, name, ids, fields, gaps in LAYERS:
        for sid in ids.split(): mapping[sid].append(code)
        layer_rows.append({'layer_id': code, 'sector': sector, 'layer': name,
            'required_fields': fields, 'source_ids': ids,
            'new_capture_sources': ' '.join(s for s in ids.split() if s in scheduled),
            'coverage_status': 'incomplete; collection does not establish field extraction or model readiness',
            'missing_or_unavailable': gaps, 'shared_requirements': 'dated identity/product/site joins; event/available/first-observed dates; units and denominators; revision and rights ledger; forward return and risk labels',
            'review_how': 'inspect original evidence, geography/entity coverage and historical window ledger; approve dated identities and units; keep private/unknown fields null'})
    write_csv(OUT / 'layer-requirements.csv', layer_rows)
    rows = load_json(ROOT / 'reports/weekly-readiness-2026-10-09/source-acceptance-records.json')
    rows.append({'source_id': 'S68', 'source_id_name_and_data': 'S68 ROR research institution identities',
        'status': 'new public identity collector', 'history_complete': False,
        'next_action': 'Review institution candidates against original trial/publication affiliation and country; request dated affiliation evidence separately.',
        'verification_required': 'Name, domain, country, aliases and relationships; institution identity does not establish affiliation, independence or historical membership.'})
    for row in rows:
        sid = row['source_id']; additions = scheduled[sid]
        row['specialist_layers'] = ' '.join(mapping[sid]) or 'shared identity, market, news, recognition or optional context'
        row['api_or_official_source'] = URLS.get(sid, 'Existing official endpoint/site access catalog: ../../../../specialist_data_collection_plan.md')
        row['new_collectors'] = '; '.join(s['source'] for s in additions)
        row['new_daily_capture'] = 'configured optima-specialist-daily.timer; native provider cadence retained' if additions else 'existing status retained; see daily_capture and next_action'
        row['new_historical_capture'] = '; '.join(s['source'] + ': 2021 onward resumable scoped windows' for s in additions if s.get('historical')) or 'no new verifiable archive configured'
        outcomes = [s['source'] + ' ' + mode + ': ' + r.get('status', 'not yet checked') + ' ' + str(r.get('records', '')) + ' ' + r.get('reason', '')
                    for s in additions for mode in ['historical', 'daily'] if (r := probe_by_mode.get((s['source'], mode)))]
        row['new_live_probe_results'] = '; '.join(outcomes) or ('not yet checked' if additions else '')
        row['scope_and_field_limits'] = '; '.join(s.get('coverage_note', 'Exact configured named query/period/geography panel; full required scope still unverified') for s in additions)
        row['historical_complete'] = 'No complete full-scope history certified'
        row['history_complete'] = False
        row['user_review_status'] = 'not yet reviewed'
        if sid in NEXT:
            row['next_action'] = NEXT[sid]
        row['review_how'] = row.get('verification_required', '') + '; compare layer-requirements.csv and original evidence; review fields/units, exact scope, historical gaps and training rights'
        if sid == 'S65':
            row['new_daily_capture'] = 'optima-search-daily.timer; existing 12-query US/English scope; USD1 per-run stop budget; monthly keyword history'
            row['scope_and_field_limits'] = 'pilot query panel only; 496-company/global query grid remains unimplemented; SERP historical rankings unavailable from live snapshots'
        if sid == 'S34': row['scope_and_field_limits'] = 'catalogue collection only; filtered payment-row API timed out; research, ownership and general payment rows remain a gap'
        if sid == 'S55': row['scope_and_field_limits'] = 'official programme page discovery only; performance/cost tables and document extraction incomplete'
        if sid == 'S47': row['scope_and_field_limits'] = 'official robotics/test-method page discovery only; not measured product benchmark results'
        if sid == 'S48': row['scope_and_field_limits'] = 'commit-pinned aggregate MLPerf measurements; older edition folders discover original performance logs and system configurations; full artifact queue, non-AI tests, entity/product links and historical availability remain incomplete'
        if sid == 'S67': row['requirement_decision'] = 'Required for layer claims using trial/fleet/yield/dispatch operational metrics; inaccessible without named owner and permitted exports; keep missing values unknown'
        if sid == 'S50': row['next_action'] = 'Official CPSC endpoint returned HTTP403. Provide approved access or official downloadable recall archive; no successful recall collection claimed.'
        if sid == 'S20': row['next_action'] = 'Official Drugs@FDA page/bulk route returned HTTP404 in host probes. Review working official download URL; original CBER samples are not a substitute.'
    write_csv(OUT / 'source-checklist.csv', rows)
    (OUT / 'source-review-records.json').write_text(json.dumps(rows, indent=2) + '\n')
    history = list(jobs(plan, universe, 'historical', date(2026, 10, 9)))
    daily = list(jobs(plan, universe, 'daily', date(2026, 10, 9)))
    counts = Counter(j['source'] for j in history)
    (OUT / 'planned-window-counts.json').write_text(json.dumps({'historical_jobs': len(history), 'daily_jobs': len(daily),
        'historical_by_source': counts, 'child_document_jobs': 'discovered dynamically from accepted literature and coverage pages'}, indent=2) + '\n')
    text = '# Specialist input coverage and capture setup — October 9, 2026\n\n'
    text += 'All 20 proposed specialist layers are mapped to required fields and sources. Full data coverage is **not complete**. Current company universe: 496 enabled companies, 388 pending identity reviews, zero accepted product records. New evidence remains excluded from training until dated identity, availability and rights checks pass.\n\n'
    text += 'Review the [68-source checklist](source-checklist.csv), [20-layer field map](layer-requirements.csv), [live provider checks](schema-probes.json), [capture plan](../../config/specialist-inputs.json), [window counts](planned-window-counts.json) and [timer verification](timer-status.txt). Existing 67-source evidence and acceptance conditions are retained with new acquisition/status columns.\n\n'
    if (OUT / 's3-probe-archive.json').exists():
        archived = load_json(OUT / 's3-probe-archive.json')
        text += 'Saved ' + str(archived['total_queued_records']) + ' validated records from ' + str(len(archived['queued_exhausted_scopes'])) + ' bounded exhausted scopes to S3, with readback hashes. [Import receipt](s3-probe-archive.json). These include context/catalogue records, not just measurements. Athena publication is queued behind existing jobs; no new query certification is claimed. Daily and historical services were started and were waiting for the shared lock at the saved timer check.\n\n'
    text += '## Additional public capture routes\n\n| Source | API/source | Historical setup | Daily scope | Remaining limit |\n|---|---|---|---|---|\n'
    for s in plan['sources']:
        if not s.get('enabled'): continue
        archive = str(counts.get(s['source'], 0)) + ' scoped windows' if s.get('historical') else 'no verified past snapshot archive'
        note = s.get('coverage_note', next((j['coverage_note'] for j in daily if j['source'] == s['source']), 'exact query panel only'))
        text += '| ' + s['source_id'] + ' ' + s['source'] + ' | [official source](' + URLS.get(s['source_id'], s['api']) + ') | ' + archive + ' | daily check at native cadence | ' + note + ' |\n'
    text += '\n## Specialist fields to review\n\n| Layer | Required evidence | Remaining gap |\n|---|---|---|\n'
    for row in layer_rows:
        text += '| ' + row['layer_id'] + ' ' + row['layer'] + ' | ' + row['required_fields'] + ' | ' + row['missing_or_unavailable'] + ' |\n'
    text += '\n## Operation and acceptance\n\nDaily source checks: 07:20 Europe/Madrid, with up to five minutes of jitter. Bounded backfill: hourly at minute 20 UTC, 24 jobs, up to six pages per job and 24 verified publications. All new heavy jobs use the existing shared lock, optima-data.slice and 512 MiB cap. Existing workers and source cursors are preserved. Lock waiting and provider outages can delay execution; enabled timers are not proof of fresh or complete data.\n\n'
    text += 'Search moves to daily at 11:00 Europe/Madrid using the already accepted 12-query scope and USD1 per-run stop budget; the weekly trigger is superseded to avoid duplicate schedules. Monthly keyword metrics and daily SERP/trend observations remain distinct. Daily capture cannot recover old SERP ranks.\n\n'
    text += 'Historical jobs start January 2021 where a real archive exists. Standard CAISO calls cover its retained 39 months; earlier history requires its [Historical OASIS downloader](https://www.caiso.com/notices/new-tool-now-available-on-caiso-oasis-website). EIA workbooks use discovered official links and reject HTML responses. Current screening lists and institution registries are never backdated. Annual trade, wage, mineral and coverage releases are checked daily without inventing daily event dates.\n\n'
    text += 'Each committed page has an immutable original document hash, validated record batch, explicit source cursor and complete/partial/failed manifest. Failed pages do not advance the cursor. Provider failures back off daily; public GitHub requests share a 40-call rolling-hour budget with hourly deferral. Pagination exhaustion and truncation checks prevent sample counts from becoming full-history claims. Partial jobs remain in the durable scheduler across dates. Literature open-access XML, versioned national coverage documents, grant institution identities and original MLPerf configurations/performance logs are queued from validated parent pages. Publication uses the isolated optima_specialist_inputs database and 100 MiB query scan cap, with S3 readback, Parquet roundtrip and partition-specific Athena count verification.\n\n'
    text += 'Before accepting a layer, reconcile entity × geography × product/site × period × field; establish currency/unit/test conditions and missing denominators; inspect raw originals and revisions; verify available-at evidence and training-use rights; and test joins to forward returns, FX, benchmarks and risk labels for both predictive models. A document count, current snapshot or name match does not satisfy this gate.\n\n'
    text += '## Inputs requiring access or additional extraction\n\nSAM requires an API key; employer boards require verified Greenhouse/Lever IDs and genuine vacancy archives; payer/society guidance, SEMI/IFR, analyst vintages, teardowns and grade-specific prices require appropriate licences; Reddit requires approved commercial access; CPSC currently returns HTTP403 and Bluesky has returned HTTP403. Trial/CRO quality measures, fleet hours/failures, chip yields and project dispatch/contract details require named owners and permitted data exports. No new account, subscription, private-data agreement or message to a provider was created.\n\n'
    text += 'The additional public APIs reduce missing collection routes, but full text still needs specialist extraction and validated company/product/person/site links. CMS Open Payments catalogue capture is not payment-row capture. DOE/NIST pages are document discovery rather than product measurements. The full MLPerf edition index, FDA inspections, guideline coverage, queues and non-US source scope remain recorded tasks rather than claimed completed feeds.\n'
    (OUT / 'capture-and-review.md').write_text(text)
    print(json.dumps({'sources_in_checklist': len(rows), 'layers': len(layer_rows), 'historical_jobs': len(history), 'daily_jobs': len(daily)}))


if __name__ == '__main__': main()
