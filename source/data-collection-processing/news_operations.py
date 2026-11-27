#!/usr/bin/env python3
"""Bounded news catch-up, historical collection and durable publication queue."""
import argparse
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import fcntl
import json
from pathlib import Path

from collection_operations import load_stored
from collection_storage import StorageSettings, now, write_json
from news_collection import NewsClient, collect, targets
from research_contract import ROOT, digest, load_json


class NewsOperations:
    def __init__(self, store, settings, config):
        self.store, self.settings, self.config = store, settings, config
        self.daily = load_json(ROOT / config['daily_config'])
        self.history = load_json(ROOT / config['historical_config'])
        self.universe = load_json(ROOT / self.daily['universe'])
        self.taxonomy = load_json(ROOT / self.daily['taxonomy'])
        if self.history['universe'] != self.daily['universe']:
            raise ValueError('news configs must use the same universe')
        identity_config = deepcopy(config)
        identity_config['historical_start'] = identity_config.pop('state_identity_historical_start', config['historical_start'])
        self.identity = digest({'config': identity_config, 'daily': self.daily, 'history': self.history,
                                'universe': digest(self.universe), 'taxonomy': digest(self.taxonomy)})
        self.prefix = 'operations/news/automation/' + self.identity

    def window(self, provider, day, mode, client, config, revision=None):
        end = day + timedelta(days=1)
        config = deepcopy(config)
        # Keep the durable daily stream and its unfinished dates. An older
        # reconciliation date can use the separately evidenced archive grant;
        # a stale Pro Light setting must not prevent that request locally.
        if provider == 'finlight' and config['providers'][provider].get('historical_access') == 'recent_only':
            from finlight_backfill import setup
            control, archive, _ = setup()
            grant = archive.get('providers', {}).get(provider, {})
            if (control['enabled'] and grant.get('historical_access') == 'observed_archive'
                    and grant.get('history_evidence') and grant.get('history_start')
                    and day >= date.fromisoformat(grant['history_start'])
                    and all(archive.get(k) == config.get(k) for k in ('universe', 'taxonomy', 'secret_id', 'region'))
                    and grant.get('secret_field') == config['providers'][provider].get('secret_field')):
                for field in ('historical_access', 'history_start', 'history_evidence'):
                    config['providers'][provider][field] = grant[field]
        if revision:
            config['reconciliation_revision'] = revision
        results = []
        for target in targets(config, self.universe, [], []):
            for language in config['providers'][provider]['languages']:
                result = collect(self.store, self.settings, self.universe, self.taxonomy,
                    config, provider, target, language, day, end, mode, client,
                    self.config['max_pages'], False, False)
                if result.get('reason') in {'news_source_changed_refresh_required', 'news_duplicate_page_refresh_required'}:
                    restart_key = self.prefix + '/restarts/' + digest({
                        'provider': provider, 'target': target, 'language': language,
                        'day': str(day), 'mode': mode, 'config': config}) + '.json'
                    previous, token = load_stored(self.store, restart_key)
                    if not previous or previous['day'] != now()[:10]:
                        write_json(self.store, restart_key, {'day': now()[:10],
                            'prior_manifest': result.get('manifest'), 'reason': result['reason']}, token)
                        result = collect(self.store, self.settings, self.universe, self.taxonomy,
                            config, provider, target, language, day, end, mode, client,
                            self.config['max_pages'], True, False)
                results.append(result)
                if result['status'] != 'complete':
                    return {'status': result['status'], 'reason': result.get('reason'), 'results': results}
        window_id = digest({'provider': provider, 'date': str(day), 'mode': mode,
                            'universe': digest(self.universe), 'targets': targets(config, self.universe, [], [])})
        item = {'window_id': window_id, 'provider': provider, 'start': str(day), 'end_exclusive': str(end),
                'mode': mode, 'manifests': sorted({r['manifest'] for r in results}), 'queued_at': now()}
        key = 'operations/news/publication-queue/' + window_id + '.json'
        previous, token = load_stored(self.store, key)
        if not previous or previous['manifests'] != item['manifests']:
            write_json(self.store, key, item, token)
        return {'status': 'complete', 'queue_key': key, 'manifests': item['manifests']}

    def run(self, clients, today=None, lanes=('daily','reconcile','historical')):
        if not lanes or set(lanes)-{'daily','reconcile','historical'}:
            raise ValueError('invalid news lanes')
        today = today or datetime.now(timezone.utc).date()
        outcomes = []
        origin = date.fromisoformat(self.config['daily_origin'])
        history_start = date.fromisoformat(self.config['historical_start'])
        for provider in sorted(self.daily['providers']):
            from source_pauses import is_paused
            if is_paused(provider):
                continue
            # Daily catch-up is always attempted first. Each lane has a separate
            # per-invocation request allowance; all use the same durable daily cap.
            for lane in lanes:
                if lane == 'historical' and provider != 'marketaux':
                    continue
                key = self.prefix + '/' + provider + '/' + lane + '.json'
                state, token = load_stored(self.store, key)
                state = state or {'next_date': str(history_start if lane == 'historical' else origin)}
                if lane == 'reconcile':
                    daily, _ = load_stored(self.store, self.prefix + '/' + provider + '/daily.json')
                    if not daily or date.fromisoformat(daily['next_date']) < today:
                        continue
                    pending = state.get('pending', [])
                    if not pending and state.get('last_cycle') != str(today):
                        pending = [str(today - timedelta(days=n)) for n in range(self.config['reconcile_days'], 0, -1)
                                   if today - timedelta(days=n) >= origin]
                        state.update(pending=pending, last_cycle=str(today))
                        token = write_json(self.store, key, state, token)
                    if not pending:
                        continue
                    day = date.fromisoformat(pending[0])
                else:
                    day = date.fromisoformat(state['next_date'])
                    if day >= (origin if lane == 'historical' else today):
                        continue
                result = self.window(provider, day, 'historical' if lane == 'historical' else 'daily',
                    clients(provider, lane), self.history if lane == 'historical' else self.daily,
                    state['last_cycle'] if lane == 'reconcile' else None)
                if result['status'] == 'complete':
                    if lane == 'reconcile':
                        state['pending'] = state['pending'][1:]
                    else:
                        state['next_date'] = str(day + timedelta(days=1))
                state.update(last_result=result, attempted_date=str(day), updated_at=now())
                write_json(self.store, key, state, token)
                outcomes.append({'provider': provider, 'lane': lane, 'date': str(day), **result})
        return {'status': 'failed' if any(r['status']=='failed' for r in outcomes) else
                'partial' if any(r['status']!='complete' for r in outcomes) else 'complete',
                'stream_id': self.identity, 'results': outcomes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'config/news-operations.json')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--lane', choices=['daily','historical','all'], default='all')
    args = parser.parse_args()
    config = load_json(args.config)
    daily = load_json(ROOT/config['daily_config'])
    settings = StorageSettings.load(ROOT/daily['storage_config'])
    with (ROOT/'.news-collection.lock').open('a') as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: return 2
        store = settings.store()
        runner = NewsOperations(store, settings, config)
        if args.status:
            states = {}
            for provider in daily['providers']:
                for lane in ('daily','historical','reconcile'):
                    states[provider+'/'+lane] = load_stored(store, runner.prefix+'/'+provider+'/'+lane+'.json')[0]
            print(json.dumps({'stream_id':runner.identity,'states':states})); return 0
        import boto3
        keys = json.loads(boto3.client('secretsmanager',region_name=daily['region']).get_secret_value(SecretId=daily['secret_id'])['SecretString'])
        def client(provider,lane):
            pc = daily['providers'][provider]
            cap = pc['max_requests_per_day']
            if provider == 'finlight':
                from finlight_backfill import setup
                control, _, archive_prefix = setup()
                if control['enabled']:
                    completed, _ = load_stored(store, archive_prefix + '/publication.json')
                    if not completed or not (completed.get('notification_message_id') or completed.get('full_text_notification_message_id')):
                        cap = control['max_requests_per_day']
            return NewsClient(store,provider,keys[pc['secret_field']],cap,config['requests_per_lane'][lane])
        report = runner.run(client, lanes=('daily','reconcile') if args.lane == 'daily' else ('historical',) if args.lane == 'historical' else ('daily','reconcile','historical'))
        from finlight_backfill import collect_archive
        report['finlight_backfill'] = ({'status':'not_selected_daily_lane'} if args.lane == 'daily' else collect_archive(runner, keys[daily['providers']['finlight']['secret_field']]))
        archive = report['finlight_backfill']
        archive_statuses = {state.get('last_result', {}).get('status')
                            for state in (archive, archive.get('earlier_archive', {}))}
        if 'failed' in archive_statuses:
            report['status'] = 'failed'
        elif 'partial' in archive_statuses and report['status'] == 'complete':
            report['status'] = 'partial'
        write_json(store, runner.prefix+'/attempts/'+digest(report)+'.json',report)
        print(json.dumps(report),flush=True)
        return 1 if report['status']=='failed' else 2 if report['status']=='partial' else 0

if __name__ == '__main__': raise SystemExit(main())
