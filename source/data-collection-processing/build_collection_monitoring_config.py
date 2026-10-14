#!/usr/bin/env python3
"""Resolve the collectors' actual stream identities into a small monitoring config."""
import json
from datetime import date, datetime, timezone
from pathlib import Path

from collection_operations import Operations, universe_windows
from collection_storage import StorageSettings
from conference_collection import VERSION as CONFERENCE_VERSION
from market_operations import MarketOperations
from news_operations import NewsOperations
from patent_backfill import Backfill
from patent_operations import PatentOperations
from research_contract import digest

ROOT = Path(__file__).resolve().parent


def load(path):
    return json.loads((ROOT/path).read_text())


def build():
    storage = load('config/collection-storage.s3.json')
    settings = StorageSettings.load(ROOT/'config/collection-storage.s3.json')
    config = {'region': storage['region'], 'bucket': storage['s3_bucket'],
              'data_prefix': storage['s3_prefix'], 'prefix': storage['s3_prefix']+'/monitoring',
              'retention_days': 30, 'heartbeat_max_age_seconds': 2700,
              'reminder_seconds': 21600, 'schedule': 'cron(5,35 * * * ? *)',
              'email': 'randall@optima-holdings.com', 'sms': '+13104033167', 'jobs': {}}
    units = load('config/ram-budget.json')['jobs']
    for unit, policy in units.items():
        duration = policy['execution_timeout']
        seconds = int(duration[:-1])*3600 if duration.endswith('h') else int(duration[:-3])*60
        daily = unit in {'optima-collection-daily.service', 'optima-nmpa-inventory.service', 'optima-patents-global-monitor.service'}
        config['jobs'][unit] = {**policy, 'queue_timeout_seconds': policy.get('queue_timeout_seconds') or 0,
            'execution_timeout_seconds': seconds, 'max_start_gap_seconds': (36 if daily else 12)*3600,
            'stale_progress_seconds': (36 if daily else 12)*3600}
    jobs = config['jobs']
    def keys(unit, values):
        jobs['optima-'+unit+'.service']['progress_keys'] = values
    raw = load('config/patent-backfill.json')
    runner = Backfill(None, settings, raw, load(raw['universe']), load(raw['taxonomy']))
    keys('patents-backfill', [runner.progress_key])
    jobs['optima-patents-backfill.service']['end_exclusive'] = raw['end_exclusive']
    keys('patents-publication', [runner.prefix+'/athena-publication/progress.json'])
    jobs['optima-patents-publication.service']['upstream_progress_key'] = runner.progress_key
    raw = load('config/patent-operations.json')
    runner = PatentOperations(None, settings, raw, load(raw['universe']), load(raw['taxonomy']))
    keys('patents-daily', [runner.prefix+'/daily/uspto/progress-'+raw['daily_origin']+'.json'])
    keys('patents-global-monitor', ['operations/patents/global-source/latest-observation.json'])
    raw = load('config/market-operations.json')
    runner = MarketOperations(None, settings, raw, load(raw['universe']), load(raw['taxonomy']))
    keys('market-collection', [runner.prefix+'/'+lane+'.json' for lane in ('daily', 'historical')])
    raw = load('config/news-operations.json')
    runner = NewsOperations(None, settings, raw)
    keys('news-collection', [runner.prefix+'/'+provider+'/'+lane+'.json'
         for provider in runner.daily['providers'] for lane in ('daily', 'historical', 'reconcile')
         if lane != 'historical' or provider == 'marketaux'])
    raw = load('config/collection-operations.json')
    today = datetime.now(timezone.utc).date()
    windows = universe_windows(raw, 'daily', date.fromisoformat(raw['daily_origin']), today, 3)
    daily_keys = []
    for window in windows:
        runner = Operations(None, settings, raw, load(window['universe']), load(raw['taxonomy']))
        daily_keys.extend(runner.prefix+'/daily/'+source+'/progress-'+str(window['origin'])+'.json' for source in raw['sources'])
    keys('collection-daily', daily_keys)
    universe, taxonomy = load('config/company-universe.v0.3.json'), load('config/sectors.v1.json')
    conference_keys = []
    for mode, origin in [('daily', '2026-09-23'), ('historical', '2021-01-01')]:
        identity = digest({'version': CONFERENCE_VERSION, 'daily_filter': 'update', 'universe': digest(universe),
                           'taxonomy': digest(taxonomy), 'mode': mode, 'origin': origin})
        conference_keys.append('operations/conferences/progress/'+identity+'.json')
    keys('conference-collection', conference_keys)
    for unit, owners in [('conference-publication', ['conferences']), ('market-publication', ['market']),
                         ('news-publication', ['news']), ('research-publication', ['sec', 'regulatory', 'disclosures', 'eodhd', 'people'])]:
        jobs['optima-'+unit+'.service']['publication_owners'] = owners
    path = ROOT/'config/collection-monitoring.json'
    if path.exists():
        previous = json.loads(path.read_text())
        for key in ('email_topic_arn', 'sms_topic_arn', 'email', 'sms', 'sms_recipients', 'sms_countries', 'email_digest_seconds', 'digest_alarm_names'):
            if key in previous:
                config[key] = previous[key]
    from monitoring_extra_jobs import extend
    extend(config)
    path.write_text(json.dumps(config, indent=2)+'\n')
    print(json.dumps({'config': str(path), 'jobs': len(jobs)}))


if __name__ == '__main__':
    build()
