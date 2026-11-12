"""Publish committed specialist windows independently of long capture jobs."""
import argparse
import fcntl
import json
from pathlib import Path
from collection_storage import StorageSettings
from research_contract import ROOT, load_json


def bridge_drugsfda_inventory(store,settings):
    from collection_storage import write_json,now
    from window_publication import list_keys
    from research_contract import digest
    count=0
    keys=[]
    for folder in ('drugsfda-inventory','ema-medicines','canada-noc','pubmed-daily','epmc-fulltext','cms-coverage','cms-payments','fda-review'):
        keys.extend(list_keys(store,settings,'constellation-backfill/specialist-publication-queue/'+folder+'/'))
    for key in keys:
        try:
            record=json.loads(store.get(key).body)
            target='operations/specialists/publication-queue/'+record['window_id']+'.json'
            prior=store.get(target)
            if prior:
                if json.loads(prior.body)['manifests']!=record['manifests']:raise ValueError('drugsfda_inventory_queue_conflict')
            else:write_json(store,target,record);count+=1
        except Exception as error:
            failure_key='operations/specialists/inventory-bridge-failures/'+digest(key)+'.json';old=store.get(failure_key)
            write_json(store,failure_key,{'key':key,'reason':type(error).__name__+': '+str(error)[:200],'at':now()},old.token if old else None)
    return count


def publication_config(settings,plan):
    return {'owner': 'specialists', 'database': 'optima_specialist_inputs',
        'workgroup': 'optima-specialist-inputs', 'region': settings.region,
        'curated_prefix': 'curated/specialists/releases', 'query_results_prefix': 'athena-results/specialists',
        'dataset': 'specialist_inputs', 'coverage_note': 'Collected source observations; source scope and completeness are recorded in each manifest. No historical-vintage or issuer-linkage inference.',
        'allowed_sources': [s['source'] for s in plan['sources'] if s.get('adapter')]}


def publish(store, settings, plan, max_windows=24, window_ids=None):
    bridge_drugsfda_inventory(store,settings)
    from window_publication import publish_pending
    from source_observation_athena import prepare
    config = publication_config(settings,plan)
    def build(s, settings, config, manifests, root):
        return prepare(s, settings, {**config, 'source_manifests': manifests}, root)
    with (ROOT / '.specialist-publication.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return publish_pending(store, settings, 'specialists', config, build,
                               ROOT / 'specialist-athena-build', max_windows=max_windows, window_ids=window_ids)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-windows',type=int,default=24)
    args=parser.parse_args()
    settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json')
    result=publish(settings.store(), settings, load_json(ROOT/'config/specialist-inputs.json'),args.max_windows)
    path=ROOT/'reports/specialist-publication-latest.json'
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'publication':result}),flush=True)
    return 1 if result['status']=='failed' else 0

if __name__=='__main__':
    raise SystemExit(main())
