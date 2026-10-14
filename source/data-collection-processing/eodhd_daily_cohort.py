#!/usr/bin/env python3
"""Collect one quota-safe EODHD inventory cohort per UTC day."""
import argparse
import fcntl
from datetime import datetime, timezone
import json
from pathlib import Path

from collection_storage import StorageSettings
from eodhd_batch import collect, make_plan
from eodhd_universe import EODHDClient, quota_batch_size
from regulatory_collection import SourceIssue
from research_contract import ROOT, digest, load_json


def manifest_keys(store,settings,universe,taxonomy):
    if not hasattr(store,'client'):raise ValueError('daily cohort runner requires S3 storage')
    relative='manifests/collection_runs/source=eodhd/dataset=company_profiles/'
    prefix=(settings.s3_prefix.rstrip('/')+'/' if settings.s3_prefix else '')+relative
    candidates={}
    paginator=store.client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=settings.s3_bucket,Prefix=prefix):
        for item in page.get('Contents',[]):
            full=item['Key']
            if not full.endswith('/final.json'):continue
            key=full[len(settings.s3_prefix.rstrip('/')+'/'):] if settings.s3_prefix else full
            manifest=json.loads(store.get(key).body);task=manifest.get('task',{})
            if manifest.get('status') in {'complete','partial','failed'} and task.get('source')=='eodhd' and task.get('dataset')=='company_profiles' and task.get('universe_hash')==digest(universe) and task.get('taxonomy_hash')==digest(taxonomy):
                # Resumed manifests contain the earlier committed pages too.
                # Re-reading every prefix repeatedly makes planning hold the
                # shared lock for hours. Drop only demonstrably covered page
                # sets; independent refreshes remain separate evidence.
                candidates.setdefault(digest(task),[]).append((key,
                    {digest(value) for value in manifest.get('pages',[])}))
    keys=[]
    for group in candidates.values():
        retained=[]
        for key,pages in sorted(group,key=lambda item:(-len(item[1]),item[0])):
            if not any(pages<=covered for _,covered in retained):
                retained.append((key,pages))
        keys.extend(key for key,_ in retained)
    return sorted(keys)


def run(args):
    settings=StorageSettings.load(args.storage_config);store=settings.store();config=load_json(args.config)
    universe=load_json(args.universe);taxonomy=load_json(args.taxonomy);client=EODHDClient.configured(config)
    day=datetime.now(timezone.utc).date().isoformat();args.report_dir.mkdir(parents=True,exist_ok=True)
    plan_path=args.report_dir/f'eodhd-auto-plan-{day}.json';result_path=args.report_dir/f'eodhd-auto-result-{day}.json'
    pending=[]
    for candidate in sorted(args.report_dir.glob('eodhd-auto-plan-*.json')):
        result_candidate=candidate.with_name(candidate.name.replace('-plan-','-result-'))
        if not result_candidate.exists() or load_json(result_candidate).get('status')!='complete':
            pending.append((candidate,result_candidate))
    if pending:
        plan_path,result_path=pending[0]
    elif result_path.exists() and load_json(result_path).get('status')=='complete':
        if not getattr(args,'top_up',False):
            return {'status':'complete','already_ran_today':True,'result_file':str(result_path)}
        number=2
        while (args.report_dir/f'eodhd-auto-plan-{day}-{number:04d}.json').exists():number+=1
        plan_path=args.report_dir/f'eodhd-auto-plan-{day}-{number:04d}.json'
        result_path=args.report_dir/f'eodhd-auto-result-{day}-{number:04d}.json'
    if not plan_path.exists():
        limit,account=quota_batch_size(client,config,args.max_profiles)
        if hasattr(client,'quota'):
            quota=client.quota.status();policy=load_json(ROOT/'config/eodhd-quota.json')
            remaining=policy['daily_group_caps']['profiles']-quota['groups'].get('profiles',0)
            limit=min(limit,max(0,remaining//config['fundamentals_general_api_calls']))
        if limit<1:return {'status':'partial','reason':'daily_quota_reserve','account':account}
        profiles=manifest_keys(store,settings,universe,taxonomy)
        plan=make_plan(store,args.inventory_manifest,profiles,limit,config)
        plan_path.write_text(json.dumps(plan,indent=2)+'\n')
    plan=load_json(plan_path);result=collect(store,settings,config,plan,client,args.workers,
        max_pages=getattr(args,'max_pages',8))
    result_path.write_text(json.dumps(result,indent=2)+'\n');return {**result,'plan_file':str(plan_path),'result_file':str(result_path)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory-manifest',default='manifests/collection_runs/source=eodhd/dataset=listing_inventory/run_4accc263-2cce-4a36-a647-e63d955517c5/final.json')
    p.add_argument('--top-up',action='store_true')
    p.add_argument('--max-profiles',type=int,default=8800);p.add_argument('--workers',type=int,default=4)
    p.add_argument('--max-pages',type=int,default=8,help='Commit at most this many 64-profile pages per invocation, then resume the pinned plan next time.')
    p.add_argument('--config',type=Path,default=ROOT/'config/eodhd-universe.json');p.add_argument('--storage-config',type=Path,default=ROOT/'config/collection-storage.s3.json')
    p.add_argument('--universe',type=Path,default=ROOT/'config/company-universe.v0.1.json');p.add_argument('--taxonomy',type=Path,default=ROOT/'config/sectors.v1.json')
    p.add_argument('--report-dir',type=Path,default=ROOT/'reports');a=p.parse_args()
    lock=(ROOT/'.eodhd-profiles.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:return 2
    try:result=run(a)
    except (ValueError,SourceIssue) as exc:
        if str(exc)=='no_remaining_symbols':result={'status':'complete','inventory_profiles_complete':True}
        else:raise
    print(json.dumps(result));return 0 if result['status']=='complete' else 2


if __name__=='__main__':raise SystemExit(main())
