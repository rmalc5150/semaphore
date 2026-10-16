"""Completion gates for publisher enrichment of existing Marketaux discovery."""
from collection_operations import load_stored
from collection_storage import StorageSettings
from research_contract import ROOT, load_json, parse_instant


def archive_ready(store, config):
    from news_operations import NewsOperations
    settings = StorageSettings.load(ROOT / config['storage_config'])
    operations = load_json(ROOT / 'config/news-operations.json')
    runner = NewsOperations(store, settings, operations)
    states = [load_stored(store, runner.prefix + '/marketaux/' + lane + '.json')[0]
              for lane in ('historical', 'daily')]
    catalog = load_json(ROOT / 'reports/committed-athena-latest.json')
    return bool(all(states) and states[0]['next_date'] >= operations['daily_origin']
        and states[1]['next_date'] >= config['end_exclusive']
        and catalog.get('status') == 'verified'
        and parse_instant(catalog['started_at']) >= max(parse_instant(s['updated_at']) for s in states))
