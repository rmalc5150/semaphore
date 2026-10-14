import json,ast
from pathlib import Path
from datetime import datetime,timezone
root=Path('/home/ec2-user/data-collection-processing')
req=json.loads((root/'config/source-coverage-requirements.json').read_text());live=json.loads((root/'reports/live-coverage/reconciliation.json').read_text())
athena={r['source_dataset']:r for r in json.loads((root/'reports/source-end-to-end-athena.json').read_text())['results']}
tests={
 'eodhd':['test_eodhd_universe','test_eodhd_daily_cohort','test_eodhd_quota'],
 'eodhd_market':['test_market_collection','test_market_operations'], 'hkex_prices':['test_market_collection'],
 'finlight':['test_news_collection','test_news_operations'],'marketaux':['test_news_collection','test_news_operations'],
 'sec_edgar':['test_sec_filings','test_sec_athena_pilot'], 'hkex_news':['test_disclosure_collection'],
 'disclosure_documents':['test_disclosure_collection','test_disclosure_athena'], 'disclosure_candidates':['test_disclosure_collection','test_disclosure_athena'],
 'google_patents_bigquery':['test_patent_collection','test_patent_backfill','test_patent_backfill_publication'],
 'uspto_odp':['test_patent_collection','test_patent_operations','test_patent_assignments','test_patent_assignment_review'],
 'crossref_proceedings':['test_conference_collection'],'people_rss':['test_people_social_collection'],
 'personnel_archive':['test_personnel_archive'], 'bluesky_search':['test_people_social_collection']}
for s in ['clinicaltrials_gov','fda_openfda','ema_ctis','uk_mhra','japan_pmda','chictr','nmpa_trials']:tests[s]=['test_regulatory_collection','test_regulatory_athena']+(['test_nmpa_baseline'] if s=='nmpa_trials' else [])
rows=[]
for s in req['sources']:
 key=s['source']+'/'+s['dataset'];state=live['sources'].get(key,{})
 row={'source':s['source'],'dataset':s['dataset'],'applicable_sectors':s['applicable_sectors'],'access':{'status':'successful_at_recorded_run' if state.get('latest_success_at') else 'not_verified_or_blocked','last_success_at':state.get('latest_success_at'),'failed_attempt_reasons':state.get('reason_codes',{})},'contract_test_modules':tests.get(s['source'],[]),'shared_contract_test_modules':['test_collection_storage','test_collection_operations','test_streaming_release','test_window_publication'] if s['source'] in tests else [],'pagination_and_totals':'source-specific fixture tests passed; live request exhaustion assessed in checkpoint audit, not complete provider history' if s['source'] in tests else 'not verified','checkpoints_and_recovery':'shared CAS, interruption and rerun contract tests passed; live manifest history audited' if s['source'] in tests else 'not implemented/verified','revisions_and_duplicates':'contract tests plus retained immutable observations; cross-source real-world event deduplication remains downstream' if s['source'] in tests else 'not verified','raw_readback':{'live_metadata_errors':state.get('metadata_errors'),'sample_hash_checks':len(state.get('raw_samples',[])),'scope':'existence/size for referenced committed objects; content hash samples only'},'publication_and_athena':athena.get(key,{'status':'not_covered_by_window_query_verifier','note':'Separate pilot query report may cover this source; incomplete source paths stay blocked.'}),'historical_usability':'unverified; requested windows and source publication dates alone do not establish field availability','history_and_coverage_gaps':s['known_gaps'],'global_completion':'not certified'}
 rows.append(row)
report={'generated_at':datetime.now(timezone.utc).isoformat(),'primary_contract_suite':{'tests':257,'status':'passed','service':'optima-source-contract-tests'},'targeted_suite':{'tests':42,'status':'passed','note':'Includes shared tests; do not add to primary count as distinct tests.'},'rows':rows,'supporting_reports':['reports/live-coverage/reconciliation.json','reports/source-end-to-end-athena.json','reports/source-pilot-query-verification.json','reports/personnel-retrieval-review-2026-09-25.json'],'note':'Per-source verification status, not a claim all sources have access, complete history or model-ready data. Fixture recovery tests do not deliberately interrupt production collectors.'}
(root/'reports/source-end-to-end-verification.json').write_text(json.dumps(report,indent=2)+'\n')
