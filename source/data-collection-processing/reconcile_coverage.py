#!/usr/bin/env python3
"""Calculate exact missing request intervals, preserving query and universe boundaries."""
import csv,json
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from research_contract import digest
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'reports/live-coverage'
def read(p):return json.loads(p.read_text())
def instant(s):return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)
def iso(d):return d.isoformat().replace('+00:00','Z')
def missing_intervals(start,end,intervals):
    start,end=instant(start),instant(end);cursor=start;gaps=[]
    for a,b in sorted((max(start,instant(a)),min(end,instant(b))) for a,b in intervals):
        if b<=a or b<=cursor:continue
        if a>cursor:gaps.append([iso(cursor),iso(a)])
        cursor=max(cursor,b)
    if cursor<end:gaps.append([iso(cursor),iso(end)])
    return gaps

def main():
 snapshot=read(OUT/'snapshot.json');cutoff=snapshot['started_at'][:10]+'T00:00:00Z';floor='2021-01-01T00:00:00Z'
 u=read(ROOT/'config/company-universe.v0.3.json');uh=digest(u)
 groups={};sources=defaultdict(lambda:{'head_statuses':Counter(),'attempt_statuses':Counter(),'reason_codes':Counter(),'latest_success_at':None,'latest_attempt_at':None,'metadata_errors':0,'committed_complete_versions':0,'publication_verified_manifests':set()})
 published=set();publication_errors=[]
 for line in (OUT/'publication-receipts.jsonl').open():
    row=json.loads(line)
    if row['errors']:publication_errors.append(row)
    else:published.update(row['receipt'].get('manifests',[]))
 patent_path=OUT/'patent-publication-receipts.json'
 if patent_path.exists():
    for row in read(patent_path):
        if row['errors']:publication_errors.append(row)
        else:published.add(row['receipt']['source']['manifest'])
 def group(task):
    # Never collapse different universe versions or query parameters.
    identity={k:v for k,v in task.items() if k not in ('window','mode')};key=digest(identity)
    if key not in groups:
        scope=task['scope']
        groups[key]={'query_id':key,'source':task['source'],'dataset':task['dataset'],'universe_hash':task['universe_hash'],'scope_hash':digest(scope),'scope_summary':{k:v for k,v in scope.items() if k in ['symbol','candidate_listing_ids','target','language','query','selection','date_basis','date_filter','feed_name','feed_url','registry_ids','ciks']},'intervals':[],'published_intervals':[],'attempts':[],'expected_unit':'observed exact query scope; requirements provisional','company_ids':scope.get('company_ids',scope.get('target',{}).get('company_ids',[]))}
    return groups[key]
 for line in (OUT/'checkpoints.jsonl').open():
    row=json.loads(line)
    if 'task' not in row:continue
    t=row['task'];g=group(t);s=sources[t['source']+'/'+t['dataset']];s['head_statuses'][row['head_status']]+=1
    s['metadata_errors']+=len(row['errors'])
    for v in row['versions']:
        s['attempt_statuses'][v['status']]+=1;s['metadata_errors']+=len(v['errors'])
        if v.get('reason_code'):s['reason_codes'][v['reason_code']]+=1
        at=v.get('finished_at')
        if at and (not s['latest_attempt_at'] or at>s['latest_attempt_at']):s['latest_attempt_at']=at
        interval=[t['window']['start'],t['window']['end']]
        g['attempts'].append({'window':interval,'status':v['status'],'reason':v['reason_code'],'manifest':v['manifest'],'records':v['records']})
        if v['complete_metadata_valid'] and not row['errors']:
            g['intervals'].append(interval);s['committed_complete_versions']+=1
            if at and (not s['latest_success_at'] or at>s['latest_success_at']):s['latest_success_at']=at
            if v['manifest'] in published:
                g['published_intervals'].append(interval);s['publication_verified_manifests'].add(v['manifest'])
 # Seed every configured market symbol so never-attempted companies do not disappear.
 from market_operations import symbols
 taxonomy=read(ROOT/'config/sectors.v1.json')
 from market_collection import spec
 from datetime import date
 listing_company={l['listing_id']:l['company_id'] for l in u['listings']}
 market_template=None
 for symbol,ids in symbols(u).items():
    scope={'symbol':symbol,'kinds':['prices','dividends','splits'],'candidate_listing_ids':ids,'end_policy':'exclusive'}
    if market_template is None:market_template=spec(u,taxonomy,'eodhd_market',date(2021,1,1),date(2022,1,1),'historical',scope)
    task={**market_template,'scope':scope}
    g=group(task);g['expected_unit']='configured current-universe market symbol';g['company_ids']=sorted({listing_company[x] for x in ids})
 # Seed daily/historical news queries directly from the configured runner contracts.
 from news_collection import targets,query_text,VERSION
 from collection_storage import task_spec
 for filename,providers in [('news-collection.json',['finlight','marketaux']),('news-history-marketaux.json',['marketaux'])]:
    cfg=read(ROOT/'config'/filename)
    for provider in providers:
        pc=cfg['providers'][provider]
        for target in targets(cfg,u,[],[]):
            for language in pc['languages']:
                scope={'target':target,'language':language,'query':query_text(provider,target['terms']),'page_size':pc['page_size'],'history_start':pc['history_start'],'history_evidence':pc['history_evidence'],'configuration_hash':digest(cfg),'completion_basis':'exhausted_provider_search_not_global_news_census'}
                task={**market_template,'source':provider,'dataset':'news_articles','collector_version':VERSION,'scope':scope,'window':{'start':floor,'end':cutoff},'mode':'historical'}
                ng=group(task)
                ng['expected_unit']='configured sector/language news query; not company-specific coverage'
                ng['configured_required_start']=floor if filename=='news-history-marketaux.json' else '2026-09-23T00:00:00Z'
                ng['configured_required_end_exclusive']='2026-09-23T00:00:00Z' if filename=='news-history-marketaux.json' else cutoff
 # Explicitly required but not yet implemented sources: all enabled companies.
 current_requirements=read(ROOT/'config/source-coverage-requirements.json')
 current_universe=read(ROOT/current_requirements['universe'])
 for source,dataset in [('reddit','social_records'),('search_rankings','search_rankings')]:
    for c in current_universe['companies']:
        if not c.get('collection_enabled'):continue
        t={'source':source,'dataset':dataset,'universe_hash':digest(current_universe),'collector_version':'required-not-implemented','scope':{'company_ids':[c['company_id']]}}
        group(t)['expected_unit']='required tracked-company candidate; exact provider/query contract pending'
 samples=[json.loads(x) for x in (OUT/'raw-samples.jsonl').open()]
 for g in groups.values():
    s=g['source'];scope=g['scope_summary'];start,end=floor,cutoff
    g['gap_basis']='missing committed complete request intervals; not proof of absent real-world events'
    # Snapshot and parent-cohort scopes cannot be interpreted as calendar-history coverage.
    snapshot_only=s in {'eodhd','people_rss','personnel_archive','disclosure_documents','disclosure_candidates','nmpa_trials','uk_mhra','japan_pmda','chictr'}
    if snapshot_only:
        g['required_start']=None;g['required_end_exclusive']=None;g['missing_request_intervals']=None;g['missing_published_intervals']=None
        g['gap_basis']='Snapshot/parent-cohort semantics: exact historical gaps cannot be established by subtracting requested dates. Inspect parent coverage and establish source history contract.'
    else:
        if s=='finlight':start='2026-09-23T00:00:00Z';g['unsupported_historical_requirement']=[floor,start]
        if s=='crossref_proceedings' and scope.get('date_filter')=='update':start='2026-09-23T00:00:00Z'
        start=g.get('configured_required_start',start);end=g.get('configured_required_end_exclusive',end)
        g['required_start']=start;g['required_end_exclusive']=end
        g['missing_request_intervals']=missing_intervals(start,end,g['intervals'])
        g['missing_published_intervals']=missing_intervals(start,end,g['published_intervals'])
    g['historical_usability']='not established: completion does not verify original field availability, identity, revisions or historical watchlist membership'
 for key,s in sources.items():
    s['publication_verified_manifest_count']=len(s.pop('publication_verified_manifests'))
    s['raw_samples']=[x for x in samples if x['source']+'/'+x['dataset']==key]
    s['access_assessment']='No successful complete run found' if not s['latest_success_at'] else 'Successful committed collection at recorded time; not a new provider entitlement test'
    s['point_in_time_usable']=None
    s['point_in_time_status']='not established'
 report={'snapshot':snapshot,'required_end_exclusive':cutoff,'historical_start':floor,'sources':dict(sources),'query_groups':list(groups.values()),'publication_receipt_errors':publication_errors,'limitations':['Exact gaps are request-interval complements for the same query contract; not missing trading sessions or missing events.','Calendar requirements before IPO/listing and after delisting need lifecycle adjudication; never treat them automatically as provider failure.','Old and current universe/configuration scopes remain separate.','Active partition receipts may replace older versions; missing publication receipt does not prove no pilot publication.','Raw content hashes and availability fields sampled, not exhaustively scanned.','No provider chosen for historical rankings; Reddit access/history unresolved.']}
 (OUT/'reconciliation.json').write_text(json.dumps(report,indent=2)+'\n')
 fields=['source','dataset','query_id','company_ids','scope_summary','universe_hash','expected_unit','required_start','required_end_exclusive','gap_basis','missing_request_intervals','missing_published_intervals','historical_usability']
 with (OUT/'query-date-gaps.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
    for g in groups.values():writer.writerow({k:json.dumps(g[k],ensure_ascii=False) if isinstance(g.get(k),(dict,list)) else g.get(k) for k in fields})
 summary={'sources':len(sources),'query_groups':len(groups),'metadata_errors':sum(s['metadata_errors'] for s in sources.values()),'receipt_errors':len(publication_errors),'sample_hash_failures':sum(not x['hash_valid'] or not x['records_valid'] for x in samples),'market_symbols':sum(g['expected_unit']=='configured current-universe market symbol' for g in groups.values()),'market_symbols_without_complete_window':sum(g['expected_unit']=='configured current-universe market symbol' and not g['intervals'] for g in groups.values()),'market_symbols_with_missing_request_intervals':sum(g['expected_unit']=='configured current-universe market symbol' and bool(g['missing_request_intervals']) for g in groups.values())}
 (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
