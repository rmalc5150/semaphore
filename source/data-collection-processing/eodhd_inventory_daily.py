"""Refresh the EODHD common-stock inventory and advance a committed S3 pointer."""
import json
from collection_storage import StorageSettings, write_json, now
from research_contract import ROOT, load_json
from eodhd_universe import EODHDClient, exchange_directory, collect_inventory


def main():
    settings = StorageSettings.load(ROOT / 'config/collection-storage.s3.json')
    store = settings.store()
    config = load_json(ROOT / 'config/eodhd-universe.json')
    universe = load_json(ROOT / 'config/company-universe.v0.1.json')
    taxonomy = load_json(ROOT / 'config/sectors.v1.json')
    client = EODHDClient.configured(config)
    exchanges, raw, url = exchange_directory(client, config)
    result = collect_inventory(store, settings, universe, taxonomy, config, exchanges, raw, url,
                               ('active', 'delisted'), client)
    if result['status'] == 'complete':
        key = 'operations/eodhd/latest-inventory.json'
        previous = store.get(key)
        write_json(store, key, {'manifest': result['manifest'], 'updated_at': now(),
                               'exchange_count': len(exchanges), 'instrument_type': 'common_stock'},
                   previous.token if previous else None)
    print(json.dumps(result), flush=True)
    return 0 if result['status'] == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
