"""Refresh the local public-source rollout ledger from durable collection evidence."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from constellation.control import Control
from public_source_capture import PREFIX,read_json,put,encode
ROOT=Path(__file__).resolve().parents[1]
DESTINATION=ROOT.parent/'public-source-rollout-2026-10-26.md'

def state_key(source,mode):
    revision=source.get('raw_content_revision')
    return PREFIX+'/states/'+mode+'/'+source['source']+(('/'+revision)if revision else'')+'.json'

def artifact_summary(state):
    if state is None:return 'waiting for first attempt'
    documents=sum(r.get('kind')=='public_document' for r in state.get('done',{}).values())
    pages=len(state.get('done',{}))-documents
    pending=len(state.get('frontier',[]));failed=len(state.get('failures',{}))
    return f'{documents} files; {pages} pages; {pending} pending; {failed} errors'

def native_summary(state):
    if state is None:return 'scheduled; waiting for first attempt'
    jobs=list(state.get('jobs',{}).values())
    return '; '.join([f"{sum(j.get('status')==s for j in jobs)} {s}" for s in ('complete','partial','failed')])+f"; {sum(j.get('records') or 0 for j in jobs):,} captured observations"

def main():
    c=Control();sources=json.loads((ROOT/'config/constellation-public-sources.json').read_text())['sources']
    native=[s for s in json.loads((ROOT/'constellation/expansion/new-adapters.json').read_text()) if s['adapter'] not in ('fred','dart')]
    keys=[]
    for source in sources:
        for mode in ('daily','historical'):keys.append(state_key(source,mode))
    for source in native:
        keys.extend(['research-data/constellation-backfill/daily-api-schedulers/'+source['source']+'/daily.json','research-data/constellation-backfill/specialist-schedulers/constellation-specialist-'+source['source']+'.service/historical.json'])
    def fetch(key):return key,read_json(c.s3,key)[0]
    with ThreadPoolExecutor(max_workers=6) as pool:states=dict(pool.map(fetch,keys))
    missing={j['manifest'] for state in states.values() if state for j in state.get('jobs',{}).values()
        if j.get('records') is None and j.get('manifest','').startswith('manifests/collection_runs/')}
    with ThreadPoolExecutor(max_workers=6) as pool:
        finals=dict(pool.map(fetch,['research-data/'+key for key in missing]))
    for state in states.values():
        for job in (state or {}).get('jobs',{}).values():
            manifest=finals.get('research-data/'+job.get('manifest',''))
            if job.get('records') is None and manifest:job['records']=manifest.get('record_count',0)
    at=datetime.now(ZoneInfo('Europe/Madrid')).strftime('%Y-%m-%d %H:%M:%S %Z')
    rows=[]
    for source in sources:
        daily=states[state_key(source,'daily')];historical=states[state_key(source,'historical')]
        errors=sorted({r['reason'] for d in (daily,historical) if d for r in d.get('failures',{}).values()})
        rows.append({'catalog_entry':source['catalog_entry'],'source':source['source'],'name':source['name'],'daily':daily,'historical':historical,'errors':errors,'scope_note':source['scope_note'],'enabled':source.get('enabled',True)})
    captured=sum(bool((r['daily'] or {}).get('done') or (r['historical'] or {}).get('done')) for r in rows)
    documents=sum(any(v.get('kind')=='public_document' for d in (r['daily'],r['historical']) if d for v in d.get('done',{}).values()) for r in rows)
    attempts={mode:sum(r[mode] is not None for r in rows) for mode in ('daily','historical')}
    report={'at':at,'archive_sources':len(rows),'native_public_api_sources':len(native),'sources_with_any_capture':captured,'sources_with_downloaded_files':documents,'attempted_sources':attempts,'rows':rows}
    (ROOT/'constellation/expansion/public-status.json').write_text(json.dumps(report,indent=2)+'\n')
    put(c.s3,c.config['prefix']+'/monitoring/public-source-rollout.json',encode(report))
    lines=['# Public-source collection rollout', '',f'Updated **{at}**. This file refreshes every five minutes from S3 evidence.', '',
        '**Collection controls:** historical '+('enabled' if c.allowed() else 'paused')+'; daily capture '+('enabled on t3' if c.daily_allowed() else 'paused')+'.', '',
        '**Placement:** daily capture on t3; historical worker '+c.config.get('worker_instance_type','c7i.4xlarge')+'. '+('The historical worker is undergoing a resize; processing is paused until its planned resource limits are installed.' if c.config.get('worker_resize_plan',{}).get('limits_installation_pending') else str(c.config['worker_pool']['total_workers'])+' configured workers share a '+str(c.config['worker_pool']['cpu_capacity'])+'-CPU / '+str(c.config['worker_pool']['memory_max_gib'])+'-GiB cap.') , '',
        f'**Configured:** {len(rows)} public archive/document routes, {len(native)} structured API collectors, and daily capture for the three already-running raw historical sources (USGS, NSF and arXiv). EPO OPS uses its stored credentials; the other new structured API routes are public. Paused archive rows remain visible as retained evidence; Decodo uses the existing credential.', '',
        f'**Observed:** {attempts["daily"]}/{len(rows)} archive sources attempted by daily capture; {attempts["historical"]}/{len(rows)} attempted by historical retrieval. {captured} have saved at least one artifact; {documents} have downloaded at least one non-HTML file. Errors below remain incomplete and retryable.', '',
        '**Scope:** archive pages are discovery evidence. Downloaded files are raw captures. Neither establishes a complete structured dataset, coverage since 2016, original historical vintages, or Athena access to the file contents. Report summaries are distinct from licensed full products. API documentation/catalog captures are labelled metadata/discovery until a dataset adapter or resource downloader is implemented.', '',
        '## Public archives and downloads', '', '| # | Source | Daily on t3 | Historical on c7i | Current error codes |', '|---|---|---|---|---|']
    for row in rows:
        daily=artifact_summary(row['daily']) if row['enabled'] else 'PAUSED — retained prior evidence only'
        historical=artifact_summary(row['historical']) if row['enabled'] else 'PAUSED — retained prior evidence only'
        lines.append(f"| {row['catalog_entry']} | {row['name']} | {daily} | {historical} | {', '.join(row['errors']) or 'none'} |")
    lines.extend(['','## Structured public APIs','','Daily task windows record when a snapshot was observed; `job.parameters.data_start/data_end` identify the provider event-date query. Daily queries overlap seven days; NASA allows three days of publication lag. Historical tasks start in 2016 where the provider has records. Completed tasks describe their configured query, not the entire provider. Counts include committed pages from incomplete tasks and may include overlapping queries or repeated snapshots; they are not unique-publication counts.','','| # | Source | Daily on t3 | Historical on c7i |','|---|---|---|---|'])
    for source in native:
        daily=states['research-data/constellation-backfill/daily-api-schedulers/'+source['source']+'/daily.json'];historical=states['research-data/constellation-backfill/specialist-schedulers/constellation-specialist-'+source['source']+'.service/historical.json']
        lines.append(f"| {source['entry']} | {source['source']} | {native_summary(daily)} | {native_summary(historical)} |")
    lines.extend(['','USGS and NSF daily capture share the historical collectors’ request budgets and defer when those budgets are exhausted. arXiv daily capture shares the cross-host single-connection lock and four-second pacing. These daily captures retain raw responses and source records in S3 under `research-data/constellation-backfill/daily-raw/`; no Athena publication of these new daily records is claimed here.','','## Athena artifact inventory','','The following live table contains verified artifact metadata for the archive/document routes. It distinguishes `discovery_page` from `public_document`. It does **not** parse binary files into analytical rows. The raw files are linked by `artifact_uri`. The earlier source-status audit remains at [data-source-status-2026-10-26.md](data-source-status-2026-10-26.md).','','```sql','SELECT catalog_entry, source, mode, artifact_kind, retrieved_at,','       artifact_uri, bytes, sha256, scope_note','FROM optima_regulatory_pilot.constellation_public_artifacts',"WHERE source = 'sia_wsts_public_semiconductor_sales'",'ORDER BY retrieved_at DESC;','```','','Use the source key below for another source. Structured API records use native collection manifests and await verified publication; this inventory is not their analytical table.','','| # | Source key | Selected scope |','|---|---|---|'])
    for source in sources:lines.append(f"| {source['catalog_entry']} | `{source['source']}` | {source['scope_note'].replace('|','/')} |")
    lines.extend(['','## Remaining work and access boundaries','','API-key, approval and commercial-only sources remain on their existing access gates. Decodo is an access layer and cannot supply a missing publisher subscription. Reddit, Bluesky, GitHub SDK and Marketaux retain their existing pauses. Internal derived routes depend on their upstream data; they are not additional external publishers.','','Full date coverage and source-specific parsing/pagination are still required for discovery-only routes, metadata samples, large files rejected by the size limit and archives beyond the bounded crawl. A 2016 target alone never makes those intervals complete. All attempted errors are recorded; only verified dated gaps longer than five days qualify for the existing gap action flag. Unknown date coverage is recorded as unaudited.'])
    temporary=DESTINATION.with_suffix('.md.updated');temporary.write_text('\n'.join(lines)+'\n');temporary.replace(DESTINATION)
    print(json.dumps({k:v for k,v in report.items() if k!='rows'}))

if __name__=='__main__':main()
