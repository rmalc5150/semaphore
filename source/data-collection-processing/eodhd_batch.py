#!/usr/bin/env python3
"""Pinned broad profile cohorts, reusable evidence and bounded parallel fetches."""
import argparse
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, now, task_spec, write_json
from disclosure_collection import finish_error, midnight
from eodhd_coverage import read_records
from eodhd_universe import EODHDClient, profile_record, quota_batch_size, valid_symbol
from regulatory_collection import CompanyMatcher, EvidenceClient, SourceIssue, require
from research_contract import ROOT, digest, load_json


def make_plan(store,inventory_key,profile_keys,limit,config):
    require(isinstance(limit,int) and limit>0,'invalid_cohort_limit')
    buckets=defaultdict(set)
    def inventory_row(record):
        p=record['payload'];buckets[(p['requested_exchange'],p['listing_status'])].add(p['provider_symbol'])
    inventory,_=read_records(store,inventory_key,'listing_inventory',inventory_row)
    require(inventory['status']=='complete','inventory_not_complete')
    reused=set();inputs=[]
    for key in sorted(set(profile_keys)):
        manifest,rows=read_records(store,key,'company_profiles')
        require(all(manifest['task'][k]==inventory['task'][k] for k in ('universe_hash','taxonomy_hash')),'profile_configuration_mismatch')
        reused.update(r['payload']['provider_symbol'] for r in rows)
        inputs.append({'key':key,'sha256':hashlib.sha256(store.get(key).body).hexdigest()})
    all_symbols=set().union(*buckets.values())
    queues=[deque(sorted(values-reused)) for _,values in sorted(buckets.items())]
    symbols=[];seen=set()
    while queues and len(symbols)<limit:
        next_queues=[]
        for queue in queues:
            while queue and queue[0] in seen:queue.popleft()
            if queue and len(symbols)<limit:
                symbol=queue.popleft();require(valid_symbol(symbol),'invalid_inventory_symbol')
                symbols.append(symbol);seen.add(symbol)
            if queue:next_queues.append(queue)
        queues=next_queues
    require(symbols,'no_remaining_symbols')
    plan={'version':'eodhd-broad-cohort-1.0','created_at':now(),
        'inventory_manifest':inventory_key,'inventory_sha256':hashlib.sha256(store.get(inventory_key).body).hexdigest(),
        'universe_hash':inventory['task']['universe_hash'],'taxonomy_hash':inventory['task']['taxonomy_hash'],
        'profile_inputs':inputs,'symbols':symbols,'inventory_symbols':len(all_symbols),
        'reused_inventory_symbols':len(reused&all_symbols),'remaining_after_cohort':len(all_symbols-reused-seen),
        'classification_rules':config['sector_patterns'],'rules_version':config['sector_rules_version'],
        'selection':'Round-robin by exchange code and active/delisted status; exact symbols pinned. Not a statistical sample.'}
    plan['plan_id']=digest(plan)
    return plan


def fetch(client,symbol):
    try:
        general,raw,url=client.get('fundamentals/'+quote(symbol,safe=''),{'filter':'General'})
        if not general:return None,raw,url,'empty_response'
        if not isinstance(general,dict) or general.get('Code')!=symbol.rsplit('.',1)[0] or not general.get('Name'):
            return None,raw,url,'identity_mismatch'
        return general,raw,url,'available'
    except SourceIssue as exc:
        if exc.code=='eodhd_http_404' and hasattr(exc,'raw'):
            return None,exc.raw,exc.public_url,'not_found'
        raise


def collect(store,settings,config,plan,client,workers=4,max_pages=None):
    require(plan['plan_id']==digest({k:v for k,v in plan.items() if k!='plan_id'}),'plan_checksum_mismatch')
    require(config['sector_patterns']==plan['classification_rules'] and config['sector_rules_version']==plan['rules_version'],
        'plan_rules_changed')
    require(1<=workers<=4,'invalid_worker_count')
    require(max_pages is None or (type(max_pages)==int and max_pages>0),'invalid_page_budget')
    for ref in [{'key':plan['inventory_manifest'],'sha256':plan['inventory_sha256']},*plan['profile_inputs']]:
        obj=store.get(ref['key']);require(obj is not None and hashlib.sha256(obj.body).hexdigest()==ref['sha256'],'plan_input_changed')
    universe=json.loads(store.get('manifests/configurations/universe/'+plan['universe_hash']+'.json').body)
    taxonomy=json.loads(store.get('manifests/configurations/taxonomy/'+plan['taxonomy_hash']+'.json').body)
    require(digest(universe)==plan['universe_hash'] and digest(taxonomy)==plan['taxonomy_hash'],'plan_configuration_changed')
    day=datetime.fromisoformat(plan['created_at'].replace('Z','+00:00')).date()
    spec=task_spec('eodhd','company_profiles','daily',midnight(day),midnight(day+timedelta(days=1)),
        {'plan_id':plan['plan_id'],'symbols':plan['symbols'],'inventory_manifest':plan['inventory_manifest'],
         'classification_rules':plan['classification_rules'],'rules_version':plan['rules_version'],
         'coverage':'Complete means all pinned cohort symbols attempted; unavailable outcomes and the uncollected global remainder remain explicit.'},
        'eodhd-broad-cohort-1.0',universe,taxonomy)
    head=store.get('checkpoints/task_'+digest(spec)+'/head.json')
    require(head is None or json.loads(head.body)['status']!='running','cohort_worker_already_running')
    write_json(store,'manifests/eodhd_plans/'+plan['plan_id']+'.json',plan)
    try:run=CollectionRun.start(store,spec,universe,taxonomy,settings,resume=True)
    except AlreadyComplete as exc:return {'status':'complete','already_complete':True,'manifest':str(exc)}
    evidence=EvidenceClient(store,'eodhd');matcher=CompanyMatcher(universe);symbols=plan['symbols']
    try:
        offset=int(run.cursor or 0)
        committed_pages=0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            while not run.exhausted and offset<len(symbols):
                if max_pages is not None and committed_pages>=max_pages:
                    return {'status':'partial','reason':'page_limit','records':run.state['record_count'],
                            'manifest':run.finish('partial','page_limit')}
                # Leave room for four attempts per request before checking actual usage again.
                allowed,_=quota_batch_size(client,config,64*4)
                count=min(64,allowed//4,len(symbols)-offset)
                if count<1:return {'status':'partial','reason':'quota_reserve','manifest':run.finish('partial','quota_reserve')}
                cohort=symbols[offset:offset+count]
                futures=[pool.submit(fetch,client,symbol) for symbol in cohort]
                records=[];error=None
                for symbol,future in zip(cohort,futures):
                    try:
                        general,raw,url,status=future.result()
                        evidence.evidence=[];evidence.save(raw,url)
                        records.append(profile_record(run,symbol,general,status,evidence.evidence,config,matcher))
                    except Exception as exc:
                        error=exc;break
                if records:
                    offset+=len(records)
                    run.commit_page(records,next_cursor=str(offset) if offset<len(symbols) else None,exhausted=offset==len(symbols))
                    committed_pages+=1
                    print(json.dumps({'stage':'broad_profiles','records':offset,'cohort_size':len(symbols),'run_id':run.run_id}),flush=True)
                if error:raise error
        return {'status':'complete','records':run.state['record_count'],'manifest':run.finish('complete',expected_records=len(symbols))}
    except (Exception,KeyboardInterrupt) as exc:return finish_error(run,exc,evidence.evidence)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=('plan','collect'))
    p.add_argument('--inventory-manifest')
    p.add_argument('--profile-manifest',action='append',default=[])
    p.add_argument('--limit',type=int,default=1024)
    p.add_argument('--plan-file',type=Path,required=True)
    p.add_argument('--result-file',type=Path)
    p.add_argument('--config',type=Path,default=ROOT/'config/eodhd-universe.json')
    p.add_argument('--storage-config',type=Path,default=ROOT/'config/collection-storage.s3.json')
    a=p.parse_args();settings=StorageSettings.load(a.storage_config);store=settings.store();config=load_json(a.config)
    if a.stage=='plan':
        if not a.inventory_manifest:p.error('--inventory-manifest required')
        result=make_plan(store,a.inventory_manifest,a.profile_manifest,a.limit,config)
        a.plan_file.parent.mkdir(parents=True,exist_ok=True);a.plan_file.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k not in {'symbols','classification_rules'}}),flush=True)
    else:
        result=collect(store,settings,config,load_json(a.plan_file),EODHDClient.configured(config))
        if a.result_file:
            a.result_file.parent.mkdir(parents=True,exist_ok=True);a.result_file.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
        return 0 if result['status']=='complete' else 2
    return 0


if __name__=='__main__':raise SystemExit(main())
