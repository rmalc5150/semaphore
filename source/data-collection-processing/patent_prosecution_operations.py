#!/usr/bin/env python3
"""Independent historical, incremental and older-history reconciliation streams."""
import argparse
from datetime import date, datetime, timedelta, timezone
import fcntl
import json
from pathlib import Path
from uuid import uuid4

from collection_storage import StorageSettings, now, write_json
from collection_operations import load_stored
from historical_policy import historical_start
import patent_prosecution as prosecution
from research_contract import ROOT, digest, load_json


class Operations:
    def __init__(self, store, settings, config, universe, taxonomy, client=None):
        self.store, self.settings, self.config = store, settings, config
        self.universe, self.taxonomy, self.client = universe, taxonomy, client
        self.start = date.fromisoformat(config.get('start_date', str(historical_start())))
        self.cutoff = date.fromisoformat(config['historical_end_exclusive'])
        if not self.start < self.cutoff:
            raise ValueError('invalid historical range')
        for name in ('max_windows', 'max_pages', 'max_requests', 'max_download_bytes', 'restart_cooldown_hours'):
            if type(config[name]) is not int or config[name] <= 0:
                raise ValueError('positive integer required: ' + name)
        if type(config['page_size']) is not int or not 1 <= config['page_size'] <= 20:
            raise ValueError('page_size must be 1..20')
        self.identity = digest({'version': prosecution.VERSION, 'start': str(self.start), 'cutoff': str(self.cutoff),
            'universe': digest(universe), 'taxonomy': digest(taxonomy), 'page_size': config['page_size']})
        self.prefix = f'operations/patents/prosecution/{self.identity}'

    def progress_key(self, dataset, mode):
        return f'{self.prefix}/{dataset}/{mode}/progress.json'

    def status(self):
        return {'stream_id': self.identity, 'historical_start': str(self.start),
            'historical_end_exclusive': str(self.cutoff), 'datasets': {dataset: {mode:
                load_stored(self.store, self.progress_key(dataset, mode))[0]
                for mode in ('historical', 'daily', 'reconcile')} for dataset in prosecution.DATASETS}}

    def run(self, dataset, mode, today):
        key = self.progress_key(dataset, mode)
        progress, token = load_stored(self.store, key)
        origin = self.cutoff if mode == 'daily' else self.start
        cursor = date.fromisoformat(progress['next_date']) if progress else origin
        end = today if mode == 'daily' else self.cutoff
        if mode == 'reconcile' and cursor >= end:
            cursor = origin
        results = []
        for _ in range(self.config['max_windows']):
            if cursor >= end:
                break
            following = cursor + timedelta(days=1)
            refresh = mode == 'reconcile'
            previous = progress.get('last_result', {}) if progress else {}
            if previous.get('reason') == 'source_changed_refresh_required':
                last = datetime.fromisoformat(progress['updated_at'].replace('Z', '+00:00'))
                if (datetime.now(timezone.utc) - last).total_seconds() < self.config['restart_cooldown_hours'] * 3600:
                    return {'dataset': dataset, 'mode': mode, 'status': 'partial', 'reason': 'source_change_cooldown'}
                refresh = True
            # Continue a partial refreshed reconciliation task rather than
            # restarting it on every scheduler invocation.
            if mode == 'reconcile' and progress and progress.get('active_date') == str(cursor) and previous.get('status') != 'complete':
                refresh = previous.get('reason') == 'source_changed_refresh_required'
            client = self.client or prosecution.Client(self.store,
                max_requests=self.config['max_requests'], max_download_bytes=self.config['max_download_bytes'])
            result = prosecution.collect(self.store, self.settings, self.universe, self.taxonomy, dataset,
                cursor, following, 'daily' if mode == 'daily' else 'historical',
                page_size=self.config['page_size'], max_pages=self.config['max_pages'], refresh=refresh, client=client,
                lane='older_reconciliation' if mode == 'reconcile' else 'collection')
            results.append(result)
            print(json.dumps({'dataset': dataset, 'mode': mode, 'start': str(cursor),
                'result': result}), flush=True)
            next_date = following if result['status'] == 'complete' else cursor
            progress = {'next_date': str(next_date), 'active_date': str(cursor), 'last_result': result,
                'updated_at': now(), 'mode': mode, 'dataset': dataset,
                'coverage': 'Completed provider query windows only; no guarantee of complete US examination history.'}
            token = write_json(self.store, key, progress, token)
            cursor = next_date
            if result['status'] != 'complete':
                break
        report = {'dataset': dataset, 'mode': mode, 'next_date': str(cursor), 'end_exclusive': str(end),
            'status': 'complete' if cursor >= end else 'partial', 'windows': results, 'finished_at': now()}
        report_key = f'{self.prefix}/reports/{uuid4()}.json'
        write_json(self.store, report_key, report)
        return {**report, 'report_key': report_key}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['tick', 'historical', 'daily', 'reconcile', 'status'], default='tick', nargs='?')
    parser.add_argument('--config', type=Path, default=ROOT / 'config/patent-prosecution-operations.json')
    args = parser.parse_args(argv)
    config = load_json(args.config)
    settings = StorageSettings.load(ROOT / config['storage_config'])
    store = settings.store()
    ops = Operations(store, settings, config, load_json(ROOT / config['universe']), load_json(ROOT / config['taxonomy']))
    if args.mode == 'status':
        print(json.dumps(ops.status()), flush=True); return 0
    with (ROOT / '.patent-prosecution.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({'status': 'partial', 'reason': 'worker_running'}), flush=True); return 2
        today = datetime.now(timezone.utc).date()
        modes = ['daily', 'historical'] if args.mode == 'tick' else [args.mode]
        # Recheck recent update windows once per day with durable progress;
        # newly added old actions are also covered by the older-history sweep.
        if args.mode == 'tick':
            for dataset in prosecution.DATASETS:
                key = f'{ops.prefix}/{dataset}/daily-overlap.json'
                overlap, token = load_stored(store, key)
                if overlap is None or overlap.get('through') != str(today) or not overlap.get('complete'):
                    start = date.fromisoformat(overlap['next_date']) if overlap and not overlap.get('complete') else max(
                        ops.cutoff, today - timedelta(days=config['reconcile_days']))
                    if start < today:
                        source_changed = bool(overlap and overlap.get('result', {}).get('reason') == 'source_changed_refresh_required')
                        if source_changed and overlap.get('updated_at'):
                            last = datetime.fromisoformat(overlap['updated_at'].replace('Z', '+00:00'))
                            if (datetime.now(timezone.utc) - last).total_seconds() < config['restart_cooldown_hours'] * 3600:
                                continue
                        result = prosecution.collect(store, settings, ops.universe, ops.taxonomy, dataset,
                            start, start + timedelta(days=1), 'daily', config['page_size'], config['max_pages'],
                            refresh=source_changed or not overlap or overlap.get('active_date') != str(start),
                            client=prosecution.Client(store, max_requests=config['max_requests'],
                                max_download_bytes=config['max_download_bytes']), lane='recent_reconciliation')
                        next_date = start + timedelta(days=1) if result['status'] == 'complete' else start
                        write_json(store, key, {'through': str(today), 'next_date': str(next_date),
                            'active_date': str(start), 'complete': next_date >= today, 'result': result, 'updated_at': now()}, token)
        results = [ops.run(dataset, mode, today) for mode in modes for dataset in prosecution.DATASETS]
        if args.mode == 'tick':
            marker = f'{ops.prefix}/reconciliation-day.json'
            seen, token = load_stored(store, marker)
            if not seen or seen['day'] != str(today):
                results += [ops.run(dataset, 'reconcile', today) for dataset in prosecution.DATASETS]
                write_json(store, marker, {'day': str(today), 'results': results[-2:]}, token)
        print(json.dumps({'stream_id': ops.identity, 'results': results}), flush=True)
        return 0 if all(r['status'] == 'complete' for r in results) else 2


if __name__ == '__main__':
    raise SystemExit(main())
