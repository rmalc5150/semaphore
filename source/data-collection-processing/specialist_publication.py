"""Publish committed specialist windows independently of long capture jobs."""
import argparse
import fcntl
import json
from pathlib import Path
from collection_storage import StorageSettings
from research_contract import ROOT, load_json


def bridge_drugsfda_inventory(store,settings,max_entries=128):
    """Rotate one bounded inventory page; never rescan every saved batch."""
    from collection_storage import write_json,now
    from window_publication import list_keys
    from research_contract import digest
    if not 1<=max_entries<=512:raise ValueError('bridge page must be between 1 and 512')
    folders=('drugsfda-inventory','ema-medicines','canada-noc','pubmed-daily','epmc-fulltext','cms-coverage','cms-payments','fda-review')
    state_key='operations/specialists/inventory-bridge-cursor.json'
    saved=store.get(state_key);state=json.loads(saved.body)if saved else{'folder_index':0,'after':{}}
    index=state['folder_index']%len(folders);folder=folders[index]
    prefix='constellation-backfill/specialist-publication-queue/'+folder+'/'
    after=state.setdefault('after',{}).get(folder,'');count=0
    if hasattr(store,'root'):
        candidates=[k for k in list_keys(store,settings,prefix)if k>after]
        raw_keys=candidates[:max_entries];truncated=len(candidates)>len(raw_keys)
    else:
        base=settings.s3_prefix.rstrip('/')+'/'if settings.s3_prefix else''
        request={'Bucket':settings.s3_bucket,'Prefix':base+prefix,'MaxKeys':max_entries}
        if after:request['StartAfter']=base+after
        response=store.client.list_objects_v2(**request)
        raw_keys=[r['Key'][len(base):]for r in response.get('Contents',[])]
        truncated=response.get('IsTruncated',False)
    for key in (k for k in raw_keys if k.endswith('.json')):
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
    state['after'][folder]=raw_keys[-1]if truncated and raw_keys else''
    state.update(folder_index=(index+1)%len(folders),updated_at=now())
    write_json(store,state_key,state,saved.token if saved else None)
    print(json.dumps({'stage':'inventory_bridge_page','folder':folder,'examined':len(raw_keys),'bridged':count,'more_in_folder':truncated}),flush=True)
    return count


def publication_config(settings,plan):
    return {'owner': 'specialists', 'database': 'optima_specialist_inputs',
        'workgroup': 'optima-specialist-inputs', 'region': settings.region,
        'curated_prefix': 'curated/specialists/releases', 'query_results_prefix': 'athena-results/specialists',
        'dataset': 'specialist_inputs', 'coverage_note': 'Collected source observations; source scope and completeness are recorded in each manifest. No historical-vintage or issuer-linkage inference.',
        'allowed_sources': [s['source'] for s in plan['sources'] if s.get('adapter')]}


def publish(store, settings, plan, max_windows=24, window_ids=None, *, build_root=None):
    if window_ids is None:bridge_drugsfda_inventory(store,settings)
    from window_publication import publish_pending
    from source_observation_athena import prepare
    config = publication_config(settings,plan)
    def build(s, settings, config, manifests, root):
        return prepare(s, settings, {**config, 'source_manifests': manifests}, root)
    with (ROOT / '.specialist-publication.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return publish_pending(store, settings, 'specialists', config, build,
                               build_root or ROOT / 'specialist-athena-build', max_windows=max_windows, window_ids=window_ids)


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
