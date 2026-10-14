#!/usr/bin/env python3
"""Report committed EODHD coverage, including explicitly incomplete scans."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from collection_storage import StorageSettings, now
from regulatory_collection import require
from research_contract import ROOT, digest, validate_record


def read_records(store, key, dataset, consume=None):
    obj=store.get(key);require(obj is not None,'coverage_manifest_missing')
    manifest=json.loads(obj.body);task=manifest['task']
    require((task['source'],task['dataset'])==('eodhd',dataset),'coverage_dataset_mismatch')
    require(manifest['status'] in {'complete','partial','failed'},'coverage_manifest_not_terminal')
    task_id='task_'+digest(task)
    require(task_id==manifest['task_id'],'coverage_task_mismatch')
    head_obj=store.get('checkpoints/'+task_id+'/head.json')
    require(head_obj is not None,'coverage_checkpoint_missing')
    head=json.loads(head_obj.body)
    require(head['task']==task and key in head['terminal_history'],'coverage_manifest_not_committed')
    universe_obj=store.get('manifests/configurations/universe/'+task['universe_hash']+'.json')
    require(universe_obj is not None,'coverage_universe_missing')
    universe=json.loads(universe_obj.body)
    require(digest(universe)==task['universe_hash'],'coverage_universe_mismatch')
    rows=[];seen=set();verified=set();count=0
    for page in manifest['pages']:
        page_count=0
        for batch in page['batches']:
            value=store.get(batch['key'])
            require(value is not None and hashlib.sha256(value.body).hexdigest()==batch['sha256'],
                    'coverage_batch_checksum_mismatch')
            records=[json.loads(line) for line in value.body.splitlines()]
            require(len(records)==batch['records'] and len(value.body)==batch['bytes'],'coverage_batch_count_mismatch')
            for record in records:
                require(not validate_record(record,universe),'coverage_record_invalid')
                require(record['source']=='eodhd' and record['dataset']==dataset and
                        record['run_id']==page['run_id'],'coverage_record_scope_mismatch')
                require(record['observation_id'] not in seen,'coverage_duplicate_observation')
                seen.add(record['observation_id'])
                refs=record['payload'].get('source_evidence')
                require(refs,'coverage_evidence_missing')
                for ref in refs:
                    identity=(ref['key'],ref['sha256'])
                    if identity not in verified:
                        evidence=store.get(ref['key'])
                        require(evidence is not None and hashlib.sha256(evidence.body).hexdigest()==ref['sha256'],
                                'coverage_evidence_checksum_mismatch')
                        verified.add(identity)
                if consume is None:rows.append(record)
                else:consume(record)
                count+=1
            page_count+=len(records)
        require(page_count==page['record_count'],'coverage_page_count_mismatch')
    require(count==manifest['record_count'],'coverage_manifest_count_mismatch')
    if manifest['status']=='complete':
        require(manifest['exhausted'] and count==manifest['expected_records'],'coverage_false_completion')
    return manifest,rows


def report(store,inventory_key,profile_keys=()):
    counts=Counter();symbols=set()
    def consume_inventory(record):
        payload=record['payload']
        counts[(payload['requested_exchange'],payload['listing_status'])]+=1
        symbols.add(payload['provider_symbol'])
    inventory,_=read_records(store,inventory_key,'listing_inventory',consume_inventory)
    scope=inventory['task']['scope']
    jobs=[(row['Code'],status) for row in scope['exchanges'] for status in scope['statuses']]
    require(len(inventory['pages'])<=len(jobs),'coverage_inventory_page_overflow')
    if inventory['status']=='complete':
        require(len(inventory['pages'])==len(jobs),'coverage_inventory_request_gap')
    completed_jobs=set(jobs[:len(inventory['pages'])])
    profiles={};inputs=[]
    for key in sorted(set(profile_keys)):
        manifest,rows=read_records(store,key,'company_profiles')
        require(all(manifest['task'][field]==inventory['task'][field] for field in ('universe_hash','taxonomy_hash')),
                'coverage_configuration_mismatch')
        inputs.append({'manifest':key,'status':manifest['status'],'reason':manifest['reason_code'],
            'records':manifest['record_count'],'cursor':manifest['cursor']})
        for row in rows:
            symbol=row['payload']['provider_symbol'];previous=profiles.get(symbol)
            if previous is None or (row['ingested_at'],row['observation_id'])>(previous['ingested_at'],previous['observation_id']):
                profiles[symbol]=row
    outcomes=Counter();sectors=Counter();candidates=[];no_description=0;no_match=0
    for symbol,row in sorted(profiles.items()):
        payload=row['payload'];status=payload.get('profile_status','available')
        outcomes[status]+=1
        if status!='available':continue
        general=payload['general'];matches=payload['sector_candidates']
        no_description+=not bool((general.get('Description') or '').strip())
        no_match+=not bool(matches)
        for match in matches:sectors[match['sector_id']]+=1
        if matches:candidates.append({'provider_symbol':symbol,'name':general.get('Name'),
            'sector_candidates':matches,'observation_id':row['observation_id'],'ingested_at':row['ingested_at']})
    attempted=len(symbols & profiles.keys())
    return {'generated_at':now(),'inventory_manifest':inventory_key,'inventory_status':inventory['status'],
        'inventory_reason':inventory['reason_code'],'exchange_codes':[r['Code'] for r in inventory['task']['scope']['exchanges']],
        'listing_records':sum(counts.values()),'distinct_listing_symbols':len(symbols),
        'exchange_counts':[{'exchange':code,'status':status,'records':counts[(code,status)],
            'request_completed':(code,status) in completed_jobs} for code,status in jobs],
        'profile_inputs':inputs,'distinct_profiles_attempted':len(profiles),'profile_outcomes':dict(outcomes),
        'inventory_symbols_attempted':attempted,'inventory_symbols_not_yet_attempted':len(symbols)-attempted,
        'profiles_outside_inventory':len(profiles.keys()-symbols),'profiles_missing_description':no_description,
        'available_profiles_without_rule_match':no_match,'sector_candidate_counts':dict(sectors),
        'sector_candidates':candidates,'ready_for_universe_promotion':False,
        'coverage_note':'Counts describe provider listings and current profile observations, not unique legal companies or historical sector membership. Candidates require identity and sector review; unmatched profiles are not proven out of scope.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory-manifest',required=True)
    parser.add_argument('--profile-manifest',action='append',default=[])
    parser.add_argument('--storage-config',type=Path,default=ROOT/'config/collection-storage.s3.json')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=report(StorageSettings.load(args.storage_config).store(),args.inventory_manifest,args.profile_manifest)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key not in {'sector_candidates','exchange_counts','exchange_codes'}}),flush=True)


if __name__=='__main__':main()
