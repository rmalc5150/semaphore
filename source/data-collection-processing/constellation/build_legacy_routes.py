"""Classify installed payloads; keep source pauses and validation gates explicit."""
import json
import shlex
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MIXED={
 'optima-market-collection.service':(['market_operations.py','--lane','historical'],['--lane','daily']),
 'optima-news-collection.service':(['news_operations.py','--lane','historical'],['--lane','daily']),
 'optima-conference-collection.service':(['conference_collection.py','--mode','historical'],['--mode','daily']),
 'optima-people-collection.service':(['people_collection_operations.py','--lane','historical'],['--lane','daily']),
 'optima-patents-prosecution.service':(['patent_prosecution_operations.py','historical-only'],['daily-only'])
}


def payload(command):
    argv=shlex.split(command)
    index=next(i for i,arg in enumerate(argv) if arg.endswith('.py'))
    return [Path(argv[index]).name,*[arg.replace('/home/ec2-user/data-collection-processing/','') for arg in argv[index+1:]]]


def main():
    existing=ROOT/'config/constellation-legacy-routes.json'
    if existing.exists() and json.loads(existing.read_text()).get('bulk_collection_enabled'):
        raise RuntimeError('Refusing to replace the active historical route catalog')
    before=json.loads((ROOT/'constellation/legacy-units-before-migration.json').read_text())
    rows=[]
    for unit in before:
        name=unit['unit']
        historical=('-backfill.service' in name or '-historical.service' in name or name in {
            'optima-cms-financial-collection.service','optima-nmpa-enrichment.service'})
        if not historical or name=='optima-source-schedule-historical.service':continue
        argv=payload(unit['command'])
        requirements=['dependency_and_workspace_validation','per_provider_quota_and_entitlement_review']
        if name=='optima-authenticated-historical.service':requirements+=['shared_sam_budget_migration']
        if name=='optima-patents-backfill.service':requirements+=['google_federation_new_worker_role']
        if name=='optima-marketaux-content-backfill.service':requirements=['operator_paused']
        if any(word in name for word in ('enrichment','financial','content')):requirements+=['publication_and_notification_separation']
        rows.append({'unit':name,'original_unit':name,'route_kind':'historical_only','argv':argv,
            'start_target':'2016-01-01','end_exclusive':'2026-10-26','cadence_seconds':3600,
            'timeout_seconds':7200,'execution_enabled':False,'remaining_requirements':requirements})
    for unit,(argv,daily_args) in MIXED.items():
        rows.append({'unit':unit.replace('.service','-historical.service'),'original_unit':unit,
            'route_kind':'split_historical','argv':argv,'controller_daily_arguments':daily_args,
            'start_target':'2016-01-01','end_exclusive':'2026-10-26','cadence_seconds':3600,
            'timeout_seconds':7200,'execution_enabled':False,
            'remaining_requirements':['split_lane_regression_and_runtime_validation']+
                (['distributed_weighted_eodhd_quota'] if 'market-' in unit else [])})
    # Fixed public, bounded pilot; execution still requires a controller allowlist.
    rows.append({'unit':'constellation-core-migration-probe.service','route_kind':'migration_probe',
        'argv':['collect_historical.py','2016-01-01','2016-02-01','--config','config/core-historical-schedule.json',
            '--only','clinicaltrials','--max-windows','1','--max-pages','1','--max-records','1000'],
        'start_target':'2016-01-01','end_exclusive':'2016-02-01','cadence_seconds':3600,
        'timeout_seconds':300,'execution_enabled':True,'remaining_requirements':[]})
    result={'schema_version':1,'controller_instance_id':'i-070bab0b09f794629',
        'historical_worker_instance_id':'i-06241bd1c4e91c2fc','routes':rows,
        'daily_and_control_location':'t3','historical_execution_location':'c7i',
        'source_pauses_preserved':True,'bulk_collection_enabled':False}
    (ROOT/'config/constellation-legacy-routes.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'historical_only_routes':sum(r['route_kind']=='historical_only' for r in rows),
        'split_historical_routes':len(MIXED),'migration_probes':1,'bulk_collection_enabled':False}))


if __name__=='__main__':main()
