#!/usr/bin/env python3
"""Build a conservative source/sector register from local release verification receipts.
Read-only toward collectors, S3 and Athena. No inference of complete company coverage.
"""
import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent

def read(path):
    return json.loads(path.read_text())

def build():
    config = read(ROOT / 'config/source-coverage-requirements.json')
    universe = read(ROOT / config['universe'])
    storage = read(ROOT / 'config/collection-storage.s3.json')
    base = f"s3://{storage['s3_bucket']}/{storage['s3_prefix']}"
    now = datetime.now(timezone.utc)
    evidence = defaultdict(list)
    warnings = []
    # Snapshot path list once; concurrent publishers may add releases during this audit.
    for path in sorted(ROOT.glob('*build*/**/release.json')):
        release = read(path)
        inputs = release.get('inputs', [])
        sources = defaultdict(list)
        for item in inputs:
            match = re.search(r'source=([^/]+)/dataset=([^/]+)/', item.get('key', ''))
            if match:
                sources[match.groups()].append(item)
        if not sources:
            continue
        receipt = None
        for name in ['window-verification.json', 'athena-verification.json']:
            candidate = path.parent / name
            if candidate.exists():
                value = read(candidate)
                if value.get('status') == 'verified' and value.get('release_id') == release.get('release_id'):
                    receipt = (candidate, value)
                    break
        coverage = defaultdict(list)
        for table, item in release.get('files', {}).items():
            if 'coverage' not in table or not isinstance(item, dict) or not item.get('path'):
                continue
            parquet = path.parent / item['path']
            if not parquet.exists():
                continue
            pf = pq.ParquetFile(parquet)
            cols = [x for x in ['source_manifest','source','window_start','window_end_exclusive','mode','query_target','records','observations'] if x in pf.schema_arrow.names]
            for batch in pf.iter_batches(batch_size=32, columns=cols, use_threads=False):
                for row in batch.to_pylist():
                    coverage[row.get('source_manifest')].append(row)
        cfg = release.get('config', {})
        for key, items in sources.items():
            windows = [row for item in items for row in coverage.get(item['key'], [])]
            if not windows and release.get('window_start'):
                windows = [{k:release.get(k) for k in ['window_start','window_end_exclusive']}]
            tables = []
            if receipt:
                # A window receipt verifies partitioned tables, not the pilot DDL names.
                counts = receipt[1].get('query', receipt[1].get('queries', {}).get('table_counts', {})).get('rows', [])
                if counts and cfg.get('database'):
                    suffix = '_windows' if receipt[0].name == 'window-verification.json' else ''
                    tables = [cfg['database']+'.'+row[0]+suffix for row in counts]
            evidence[key].append({'release_id':release.get('release_id'),
                'release_file':str(path.relative_to(ROOT)),
                'release_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'input_manifests':items, 'windows':windows,
                'verification_file':str(receipt[0].relative_to(ROOT)) if receipt else None,
                'verified_at':receipt[1].get('checked_at') if receipt else None,
                'query_id':receipt[1].get('query',receipt[1].get('queries',{}).get('table_counts',{})).get('query_id') if receipt else None,
                'verified':bool(receipt), 'tables':tables,
                'curated_location':base+'/'+release['release_prefix'] if release.get('release_prefix') else None})
    sectors = universe['scope']['sector_ids']
    companies = {}
    for sector in sectors:
        selected = [c for c in universe['companies'] if c.get('collection_enabled') and any(s['sector_id']==sector for s in c.get('sectors',[]))]
        ids = {c['company_id'] for c in selected}
        listings = [l for l in universe['listings'] if l.get('company_id') in ids]
        companies[sector] = {'selection':'Current collection-enabled universe; final approved watchlist pending',
            'companies':[{'company_id':c['company_id'],'name':c['canonical_name'],'identity_status':c.get('review_status'),'domicile_country':c.get('domicile_country')} for c in selected],
            'listings':[{'listing_id':l['listing_id'],'company_id':l['company_id'],'exchange_mic':l.get('exchange_mic'),'ticker':l.get('ticker')} for l in listings],
            'geographies':sorted({c['domicile_country'] for c in selected if c.get('domicile_country')}),
            'unknown_domicile_count':sum(not c.get('domicile_country') for c in selected)}
    rows=[]
    for source in config['sources']:
        key=(source['source'],source['dataset'])
        ev=evidence.get(key,[])
        verified=[e for e in ev if e['verified']]
        windows=[w for e in verified for w in e['windows']]
        starts=sorted({w['window_start'] for w in windows if w.get('window_start')})
        ends=sorted({w['window_end_exclusive'] for w in windows if w.get('window_end_exclusive')})
        daily=sorted({w['window_end_exclusive'] for w in windows if w.get('mode')=='daily' and w.get('window_end_exclusive')})
        timestamps=sorted(e['verified_at'] for e in verified if e['verified_at'])
        lag=None
        if daily:
            lag=round((now-datetime.fromisoformat(daily[-1].replace('Z','+00:00'))).total_seconds()/3600,2)
        for sector in source['applicable_sectors']:
            rows.append({**source,'sector':sector,'required_company_set':sector,
                'required_company_count':len(companies[sector]['companies']),
                'required_geographies':'All markets in scope; company universe provisional; actual source jurisdictions and coverage vary',
                'collected':'validated release inputs observed' if ev else 'not evidenced by this inventory',
                'published':'Athena publication evidenced' if verified else 'not evidenced by matched receipt',
                'verified':'source-window count verification; sector/company completeness unverified' if verified else 'not evidenced by matched receipt',
                'sector_attribution':'Source applicability only; no claim every verified window covers this sector',
                'verified_release_count':len(verified),
                'earliest_verified_request_start':starts[0] if starts else None,
                'latest_verified_request_end_exclusive':ends[-1] if ends else None,
                'earliest_usable_date':None,'latest_usable_date':None,
                'usable_date_reason':'Point-in-time eligibility and per-company coverage not established',
                'latest_daily_request_end_exclusive':daily[-1] if daily else None,
                'daily_window_boundary_lag_hours':lag,
                'daily_freshness':'No dated verified daily window' if lag is None else ('Window boundary within proposed 48h target; company freshness unverified' if lag<=48 else 'Window boundary exceeds proposed 48h target'),
                'missing_periods':'2021-01-01 onward not fully reconciled by company/query. Verified request intervals in evidence file are not continuous coverage.',
                'raw_s3_prefix':base+f'/raw/source={key[0]}/dataset={key[1]}/' if ev else None,
                'manifest_s3_prefix':base+f'/manifests/collection_runs/source={key[0]}/dataset={key[1]}/' if ev else None,
                'curated_athena_tables':sorted({t for e in verified for t in e['tables']}),
                'curated_s3_locations':sorted({e['curated_location'] for e in verified if e['curated_location']}),
                'last_verification':timestamps[-1] if timestamps else None,
                'evidence_key':'/'.join(key)})
    live_path=ROOT/'reports/live-coverage/reconciliation.json'
    live=read(live_path) if live_path.exists() else None
    if live:
        catalog_path=ROOT/'reports/live-coverage/access-catalog.json'
        catalog=read(catalog_path) if catalog_path.exists() else {}
        for row in rows:
            status=live['sources'].get(row['evidence_key'],{})
            row['live_checkpoint_checked_at']=live['snapshot']['finished_at']
            row['live_head_statuses']=json.dumps(status.get('head_statuses',{}),sort_keys=True)
            row['live_complete_versions']=status.get('committed_complete_versions',0)
            row['live_receipted_manifest_count']=status.get('publication_verified_manifest_count',0)
            row['last_successful_collection_at']=status.get('latest_success_at')
            row['access_verification']=status.get('access_assessment','No successful committed collection or configured provider access verified')
            row['live_failure_reasons']=json.dumps(status.get('reason_codes',{}),sort_keys=True)
            row['exact_gap_report']='reports/live-coverage/query-date-gaps.csv'
            row['historical_usability']='Not established; sampled raw availability and scope semantics reported in live reconciliation'
            row['missing_periods']='Exact same-query interval complements in linked gap report; snapshot/cohort history and listing lifecycle limits explicitly unresolved'
            row['catalog_access_checked_at']=catalog.get('checked_at')
            row['catalog_tables_missing_or_unverified']=[]
            for table in row['curated_athena_tables']:
                db,name=table.split('.',1)
                if name not in {t['table'] for t in catalog.get('glue_catalog',{}).get(db,{}).get('tables',[])}:
                    row['catalog_tables_missing_or_unverified'].append(table)
            if status:
                row['raw_s3_prefix']=base+f"/raw/source={row['source']}/dataset={row['dataset']}/"
                row['manifest_s3_prefix']=base+f"/manifests/collection_runs/source={row['source']}/dataset={row['dataset']}/"
                row['collected']='Live committed complete versions: '+str(row['live_complete_versions'])+'; partial/failed attempts retained'
    fresh_path=ROOT/'reports/source-end-to-end-athena.json'
    fresh=read(fresh_path) if fresh_path.exists() else None
    fresh_by_source={r['source_dataset']:r for r in fresh['results']} if fresh else {}
    for row in rows:
        check=fresh_by_source.get(row['evidence_key'],{})
        row['fresh_athena_query_status']=check.get('status','not_checked_by_window_verifier')
        row['fresh_athena_checked_at']=check.get('checked_at')
        row['fresh_athena_query_id']=check.get('query',{}).get('query_id')
    report={'generated_at':now.isoformat(),'method':'Local immutable release metadata and matching stored Athena verification receipts; no fresh provider/S3/catalog queries. Only coverage Parquet columns read. This is an evidence inventory, not completion certification.',
        'policy':config,'company_sets':companies,'rows':rows,'warnings':warnings,
        'unmapped_observed_sources':['/'.join(k) for k in evidence if k not in {(s['source'],s['dataset']) for s in config['sources']}]}
    if live:
        report['live_reconciliation']='reports/live-coverage/reconciliation.json'
        report['method']='Live S3 checkpoints and committed terminal manifests, raw-object sizes, sampled content hashes and publication receipts reconciled with local release metadata. Live Glue catalog access checked. Stored Athena counts were not rerun; provider access is assessed at recorded run times, not by new paid requests.'
    if fresh:
        report['fresh_query_report']='reports/source-end-to-end-athena.json'
        report['method']=report['method'].replace('Stored Athena counts were not rerun;', 'Fresh bounded count queries for represented source pairs are linked;')
    out=ROOT/'reports';out.mkdir(exist_ok=True)
    (out/'source-sector-coverage.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'source-sector-coverage-evidence.json').write_text(json.dumps({'generated_at':now.isoformat(),'sources':{'/'.join(k):v for k,v in evidence.items()}},indent=2)+'\n')
    fields=[k for k in rows[0] if k not in ['applicable_sectors','curated_s3_locations']]
    with (out/'source-sector-coverage.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader()
        writer.writerows({k:('; '.join(v) if isinstance(v,list) else v) for k,v in r.items()} for r in rows)
    text=['# Source-by-sector coverage register','',f'Generated {now.isoformat()}.', '',report['method'],'',
        '**Scope:** All markets are in scope, confirmed September 25, 2026; no HKEX-only restriction. Company sets are collection-enabled candidates, not a final approved watchlist. IBKR excluded.', '',
        '**Reading the dates:** Request boundaries are not earliest/latest usable observations. Those usable-date fields remain null until historical availability and company coverage are verified. Min/max boundaries do not prove intervening coverage. Daily freshness uses a proposed 48-hour target and a request boundary, not every company’s latest record.', '',
        'Detailed files: [CSV](reports/source-sector-coverage.csv), [JSON with company/listing sets](reports/source-sector-coverage.json), [release and query receipts](reports/source-sector-coverage-evidence.json), [requirements](config/source-coverage-requirements.json).','',
        '| Sector | Collection-enabled companies | Listings | Unknown domicile |','|---|---:|---:|---:|']
    for sector,c in companies.items():text.append(f"| {sector} | {len(c['companies'])} | {len(c['listings'])} | {c['unknown_domicile_count']} |")
    text+=['','Counts can overlap across sectors. Source jurisdictions do not establish issuer domicile or exhaustive geographic coverage.','','| Source / dataset | Sectors | Implementation | Collection / publication verification | Last stored verification |','|---|---|---|---|---|']
    for source in config['sources']:
        r=next(r for r in rows if r['source']==source['source'] and r['dataset']==source['dataset'])
        text.append(f"| {r['source']} / {r['dataset']} | {', '.join(source['applicable_sectors'])} | {r['implemented']} | {r['collected']}; {r['verified_release_count']} verified releases | {r['last_verification'] or 'unknown'} |")
    text+=['','## Remaining verification','',
        '- Reconcile every required company/query/date against committed S3 checkpoints, including uncurated, failed and partial runs. Local receipts cannot enumerate all raw collections or missing periods.',
        '- Refresh live source access, Glue partitions and daily freshness; the register preserves the actual receipt verification time rather than treating this build time as a new verification.',
        '- Establish point-in-time usable dates and required company/geography scope. Sector applicability is not sector completeness.',
        '- Close Reddit and search-ranking historical access gaps, regulatory/site/KOL/policy gaps and broader conference coverage.',
        '- Refresh with `.venv-athena/bin/python source_coverage_register.py`; no collection schedules or source state are changed.','']
    if live:
        text+=['## Live reconciliation', '', 'Read [findings and limits](COVERAGE_RECONCILIATION.md), [exact query/date gaps](reports/live-coverage/query-date-gaps.csv), and [machine-readable reconciliation](reports/live-coverage/reconciliation.json).', '', 'Live snapshot completed '+live['snapshot']['finished_at']+'. Source success times, failed-attempt reasons and raw checkpoint status are included in the register CSV/JSON. Unknown point-in-time usable dates remain unknown.', '']
    (ROOT/'SOURCE_COVERAGE_REGISTER.md').write_text('\n'.join(text))
    print(json.dumps({'rows':len(rows),'sources':len(config['sources']),'observed_source_datasets':len(evidence),'unmapped':report['unmapped_observed_sources']}))

if __name__=='__main__':
    build()
