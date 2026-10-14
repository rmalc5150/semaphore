"""Publish committed specialist windows independently of long capture jobs."""
import argparse
import fcntl
import json
from pathlib import Path
from collection_storage import StorageSettings
from research_contract import ROOT, load_json


def publish(store, settings, plan, max_windows=24, window_ids=None):
    from window_publication import publish_pending
    from source_observation_athena import prepare
    config = {'owner': 'specialists', 'database': 'optima_specialist_inputs',
        'workgroup': 'optima-specialist-inputs', 'region': settings.region,
        'curated_prefix': 'curated/specialists/releases', 'query_results_prefix': 'athena-results/specialists',
        'dataset': 'specialist_inputs', 'coverage_note': 'Collected source observations; source scope and completeness are recorded in each manifest. No historical-vintage or issuer-linkage inference.',
        'allowed_sources': [s['source'] for s in plan['sources'] if s.get('adapter')]}
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
