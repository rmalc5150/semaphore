#!/usr/bin/env python3
"""Discover committed research runs and publish independently verified partitions."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import fcntl
import json
from pathlib import Path

from collection_operations import load_stored
from collection_storage import StorageSettings, now, write_json
from research_contract import ROOT, digest, load_json
from window_publication import list_keys, publish_pending
import sec_athena_pilot
import regulatory_athena
import disclosure_athena
import source_observation_athena
import patent_prosecution_athena

GROUPS = {
    'sec': ('sec-athena-pilot.json', sec_athena_pilot),
    'regulatory': ('regulatory-athena-pilot.json', regulatory_athena),
    'disclosures': ('disclosure-athena-pilot.json', disclosure_athena),
    'eodhd': ('eodhd-observations-athena.json', source_observation_athena),
    'people': ('people-observations-athena.json', source_observation_athena),
    'social': ('social-observations-athena.json', source_observation_athena),
    'patent_office_actions': ('patent-office-actions-athena.json', patent_prosecution_athena),
    'patent_petition_decisions': ('patent-petition-decisions-athena.json', patent_prosecution_athena),
}


def owner_for(task):
    source, dataset = task.get('source'), task.get('dataset')
    if source == 'uspto_odp' and dataset in {'patent_office_actions', 'patent_petition_decisions'}:
        # These are versioned observations, not distinct patent events. A
        # reconciliation task owns its own observation window; consumers join
        # document identities and choose a captured version at their cutoff.
        return dataset
    other = {('eodhd', 'company_profiles'): 'eodhd',
             ('people_rss', 'people_source_records'): 'people',
             ('personnel_archive', 'people_source_records'): 'people',
             ('bluesky_search', 'social_records'): 'social'}
    if (source, dataset) in other:
        return other[source, dataset]
    if source == 'sec_edgar' and dataset == 'filings':
        return 'sec'
    if source in {a.source for a in regulatory_athena.ADAPTERS.values()} and dataset == 'research_records':
        return 'regulatory'
    if (source, dataset) in {('hkex_news', 'filings'), ('disclosure_documents', 'documents')} or (
            source == 'disclosure_candidates' and dataset in {
                'press_releases', 'licensing_agreements', 'ma_announcements', 'strategic_transactions'}):
        return 'disclosures'
    return None


def discover(store, settings, owners=None):
    """Use committed heads; partial refreshes cannot replace successful releases."""
    counts = dict.fromkeys(GROUPS, 0)
    def inspect(key):
        head, _ = load_stored(store, key)
        task = head.get('task', {})
        owner = owner_for(task)
        if not owner or (owners and owner not in owners) or head.get('status') != 'complete':
            return None
        manifest_key = head.get('terminal_manifest')
        if not manifest_key or manifest_key not in head.get('terminal_history', []):
            raise ValueError('Uncommitted terminal manifest')
        manifest, _ = load_stored(store, manifest_key)
        if not manifest or manifest['task'] != task or manifest['status'] != 'complete' or not manifest['exhausted']:
            raise ValueError('Checkpoint/manifest mismatch')
        window_id = digest(task)
        if manifest['task_id'] != 'task_' + window_id:
            raise ValueError('Task identity mismatch')
        queue_key = f'operations/{owner}/publication-queue/{window_id}.json'
        previous, token = load_stored(store, queue_key)
        if previous and previous['manifests'] == [manifest_key]:
            return None
        return owner, queue_key, {'window_id': window_id, 'manifests': [manifest_key],
            'queued_at': now(), 'source': task['source'], 'dataset': task['dataset']}, token
    if owners and set(owners).issubset({'patent_office_actions', 'patent_petition_decisions'}):
        # A bounded prosecution publication should not read every unrelated
        # historical collector checkpoint just to find its few new windows.
        keys = set()
        for owner in owners:
            prefix = f'manifests/collection_runs/source=uspto_odp/dataset={owner}/'
            for key in list_keys(store, settings, prefix):
                if key.endswith('/final.json'):
                    manifest, _ = load_stored(store, key)
                    if manifest.get('status') == 'complete':
                        keys.add('checkpoints/task_' + digest(manifest['task']) + '/head.json')
        keys = sorted(keys)
    else:
        keys = [key for key in list_keys(store, settings, 'checkpoints/' if hasattr(store, 'root') else 'checkpoints/task_')
                if key.startswith('checkpoints/task_') and key.endswith('/head.json')]
    # Only reads overlap. Queue mutations retain conditional-write ownership.
    with ThreadPoolExecutor(max_workers=4) as pool:
        for candidate in pool.map(inspect, keys):
            if candidate:
                owner, key, item, token = candidate
                write_json(store, key, item, token)
                counts[owner] += 1
    return counts


def prepare_for(module):
    def prepare(store, settings, config, manifests, output_root):
        return module.prepare(store, settings, {**config, 'source_manifests': manifests}, output_root)
    return prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-windows', type=int, default=2)
    parser.add_argument('--owners', nargs='+', choices=sorted(GROUPS), help='Publish only selected source groups')
    args = parser.parse_args()
    if not 1 <= args.max_windows <= 24:
        parser.error('max-windows must be between 1 and 24 per source group')
    with (ROOT / '.research-athena.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 2
        settings = StorageSettings.load(ROOT / 'config/collection-storage.s3.json')
        store = settings.store()
        print(json.dumps({'discovered': discover(store, settings, args.owners)}), flush=True)
        results = {}
        for owner, (filename, module) in GROUPS.items():
            if args.owners and owner not in args.owners:
                continue
            config = load_json(ROOT / 'config' / filename)
            config.pop('source_manifests', None)
            results[owner] = publish_pending(store, settings, owner, config, prepare_for(module),
                ROOT / 'research-window-build' / owner, args.max_windows)
        print(json.dumps(results), flush=True)
        return int(any(result['status'] == 'failed' for result in results.values()))


if __name__ == '__main__':
    raise SystemExit(main())
